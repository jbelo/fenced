#!/usr/bin/env python3
"""Host-side mock consumer checks. Creates/removes only uniquely named test clients."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

CLI_SHA = "680c303326d8e9b35ae4ccb511b3b72e0d85955d3f061b5e4d0e1d481fecb0b6"
GATEWAY_ID = "sha256:0e986137eb422012efad5325c145360723bc54e371025711b69000a58ba9da50"
ROOT = Path(__file__).resolve().parents[3]


def docker(*args, check=True):
    result = subprocess.run(["docker", *args], text=True, capture_output=True,
                            timeout=60)
    if check and result.returncode:
        raise RuntimeError(f"docker {args[0]} failed: {result.stderr}")
    return result


def second_interface(image, gateway, prefix):
    """Reproduce the delivered mock on isolated networks; never attach live service."""
    networks = []
    clone = prefix + "-gateway"
    created = False
    try:
        ids = docker("network", "ls", "-q").stdout.split()
        existing = [ipaddress.ip_network(item["Subnet"]) for net in
                    json.loads(docker("network", "inspect", *ids).stdout)
                    for item in (net.get("IPAM", {}).get("Config") or []) if item.get("Subnet")]
        for suffix in ["-inside", "-outside"]:
            network = prefix + suffix
            subnet = next(ipaddress.ip_network(f"10.240.{i}.0/24") for i in range(256)
                          if not any(ipaddress.ip_network(f"10.240.{i}.0/24").overlaps(n)
                                     for n in existing if n.version == 4))
            docker("network", "create", "--internal", "--subnet", str(subnet), network)
            existing.append(subnet)
            networks.append(network)
        subnet = json.loads(docker("network", "inspect", networks[0]).stdout)[0]["IPAM"]["Config"][0]["Subnet"]
        inside_ip = str(ipaddress.ip_network(subnet).network_address + 10)
        with tempfile.TemporaryDirectory(prefix=".gateway-check-", dir=ROOT) as directory:
            folder = Path(directory)
            mounts = {m["Destination"]: m["Source"] for m in gateway["Mounts"]}
            config = json.loads(Path(mounts["/etc/agent-gateway/config.json"]).read_text())
            assert config["mode"] == "mock"
            config["listen_address"] = inside_ip + ":8080"
            (folder / "config.json").write_text(json.dumps(config))
            (folder / "policy.json").write_bytes(Path(mounts["/etc/agent-gateway/policy.json"]).read_bytes())
            (folder / "client.json").write_text(json.dumps({"gateway_url": "http://" + inside_ip + ":8080"}))
            folder.chmod(0o755)
            for path in folder.iterdir():
                path.chmod(0o644)
            docker("create", "--name", clone, "--network", networks[0], "--ip", inside_ip,
                   "--user", "10001:10001", "--read-only", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges", "--sysctl", "net.ipv4.ip_forward=0",
                   "--sysctl", "net.ipv6.conf.all.forwarding=0",
                   "--mount", f"type=bind,src={folder}/config.json,dst=/etc/agent-gateway/config.json,readonly",
                   "--mount", f"type=bind,src={folder}/policy.json,dst=/etc/agent-gateway/policy.json,readonly",
                   gateway["Image"])
            created = True
            docker("network", "connect", networks[1], clone)
            docker("start", clone)
            for _ in range(20):
                status = json.loads(docker("inspect", clone).stdout)[0]
                if status["State"].get("Health", {}).get("Status") == "healthy":
                    break
                time.sleep(1)
            else:
                raise AssertionError("isolated two-interface gateway not healthy")
            docker("run", "--rm", "--network", networks[0], "--read-only", "--user", "501:20",
                   "--mount", f"type=bind,src={folder}/client.json,dst=/tmp/client.json,readonly",
                   "-e", "AGENTCTL_CONFIG=/tmp/client.json", image, "agentctl",
                   "github", "pr", "view", "--repo", "company/project", "--number", "123")
            outside_ip = status["NetworkSettings"]["Networks"][networks[1]]["IPAddress"]
            result = docker("run", "--rm", "--network", networks[1], image, "curl",
                            "--noproxy", "*", "--max-time", "3", "-sS", "-o", "/dev/null",
                            "http://" + outside_ip + ":8080", check=False)
            assert result.returncode == 7, "secondary interface must refuse connection"
            result = docker("run", "--rm", "--network", networks[0], image, "curl",
                            "--noproxy", "", "--max-time", "3", "-x", "http://" + inside_ip + ":8080",
                            "-sS", "-o", "/dev/null", "-w", "%{http_connect}",
                            "https://api.github.com", check=False)
            assert result.returncode != 0 and result.stdout in ("400", "403", "404", "405"), (result.returncode, result.stdout, result.stderr)
            docker("rm", "-f", "-v", clone)
            created = False
    finally:
        if created:
            docker("rm", "-f", "-v", clone, check=False)
        for network in reversed(networks):
            docker("network", "rm", network, check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="go-agent-all")
    parser.add_argument("--network", default="go-agent-internal-net")
    parser.add_argument("--gateway", default="agent-gateway-mock-agent-gateway-1")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = []

    def passed(label):
        results.append(label)
        print("PASS", label, flush=True)

    gateway = json.loads(docker("inspect", args.gateway).stdout)[0]
    assert gateway["Image"] == GATEWAY_ID, "Different gateway delivery: review provenance first"
    assert gateway["State"]["Health"]["Status"] == "healthy"
    assert not gateway["HostConfig"]["PortBindings"]
    assert gateway["HostConfig"]["ReadonlyRootfs"]
    assert gateway["HostConfig"]["CapDrop"] == ["ALL"]
    assert gateway["HostConfig"]["Sysctls"]["net.ipv4.ip_forward"] == "0"
    assert gateway["HostConfig"]["Sysctls"]["net.ipv6.conf.all.forwarding"] == "0"
    assert set(gateway["NetworkSettings"]["Networks"]) == {args.network}
    assert {m["Destination"] for m in gateway["Mounts"]} == {
        "/etc/agent-gateway/config.json", "/etc/agent-gateway/policy.json"}
    assert all(not m["RW"] for m in gateway["Mounts"])
    proxy_before = hashlib.sha256((ROOT / "squid.conf").read_bytes()).hexdigest()
    passed("mock gateway identity and inspected runtime restrictions")
    names = []
    prefix = "fenced-gateway-check-" + uuid.uuid4().hex[:10]

    def start(suffix, command):
        name = prefix + suffix
        docker("run", "-d", "--name", name, "--network", args.network,
               "--read-only", "--user", "501:20", "--cap-drop=ALL",
               "--security-opt=no-new-privileges", "--tmpfs", "/tmp:rw,mode=1777",
               "-e", "HOME=/tmp", "-e", "HTTP_PROXY=http://127.0.0.1:1",
               "-e", "HTTPS_PROXY=http://127.0.0.1:1", "-e", "ALL_PROXY=http://127.0.0.1:1",
               args.image, *command)
        names.append(name)
        return name

    def execute(container, *command, check=True):
        return docker("exec", container, *command, check=check)

    try:
        client = start("-client", ["sleep", "infinity"])
        actual = execute(client, "sha256sum", "/usr/local/bin/agentctl").stdout.split()[0]
        assert actual == CLI_SHA
        cases = [
            (["github", "pr", "list", "--repo", "company/project", "--limit", "50"], 0),
            (["github", "pr", "view", "--repo", "company/project", "--number", "123"], 0),
            (["github", "pr", "diff", "--repo", "company/project", "--number", "123"], 0),
            (["github", "pr", "checks", "--repo", "company/project", "--number", "123", "--limit", "50"], 0),
            (["shortcut", "story", "get", "--workspace", "engineering", "--id", "456"], 0),
            (["shortcut", "story", "search", "--workspace", "engineering", "--text", "gateway", "--limit", "50"], 0),
            (["github", "pr", "view", "--repo", "forbidden/project", "--number", "1"], 4),
            (["github", "pr", "list", "--repo", "company/project", "--cursor", "invalid"], 2),
        ]
        for command, expected in cases:
            result = execute(client, "agentctl", *command, check=False)
            assert result.returncode == expected, (command, result.stdout, result.stderr)
            envelope = json.loads(result.stdout)
            assert envelope["version"] == "v1" and envelope["request_id"]
            if expected:
                assert envelope["error"]["code"] == {4: "policy_denied", 2: "invalid_cursor"}[expected]
            else:
                assert "data" in envelope and "error" not in envelope
            passed(" ".join(command))
        passed("proxy bypass with deliberately unusable HTTP/HTTPS/ALL proxies")
        execute(client, "sh", "-ec", '''
test "$AGENTCTL_CONFIG" = /etc/agentctl/config.json
test ! -e /var/run/docker.sock
test ! -e /etc/agent-gateway/config.json
test ! -e /etc/agent-gateway/policy.json
test ! -e /run/secrets/shortcut_engineering
test ! -e /usr/local/bin/agent-gateway
! (printf x >> /etc/agentctl/config.json) 2>/dev/null
! (printf x >> /usr/local/bin/agentctl) 2>/dev/null
''')
        passed("protected CLI/config; no server configuration, policy, credential mount or Docker socket")
        for url in ["https://api.github.com", "https://api.app.shortcut.com"]:
            result = execute(client, "curl", "--max-time", "8", "--noproxy", "", "-x",
                             "http://go-agent-egress-proxy:3128", "-sS", "-o", "/dev/null",
                             "-w", "%{http_connect}", url, check=False)
            assert result.stdout == "403", result
            direct = execute(client, "curl", "--max-time", "3", "--noproxy", "*",
                             "-sS", "-o", "/dev/null", url, check=False)
            assert direct.returncode != 0
        passed("GitHub/Shortcut denied through shared proxy and direct network access")

        # A real member-to-member request schedules a fixed read in the worker.
        worker_code = '''const http=require('http'),fs=require('fs'),cp=require('child_process');
http.createServer((req,res)=>{if(req.url!='/start'){res.writeHead(404);res.end();return;}
setTimeout(()=>{let r=cp.spawnSync('agentctl',['github','pr','view','--repo','company/project','--number','123'],{encoding:'utf8'});
fs.writeFileSync('/tmp/result',JSON.stringify({exit:r.status,body:r.stdout}));},2500);
res.end('scheduled');}).listen(18888,'0.0.0.0');'''
        worker = start("-worker", ["node", "-e", worker_code])
        for _ in range(20):
            probe = execute(client, "curl", "--noproxy", "*", "--max-time", "2", "-fsS",
                            f"http://{worker}:18888/start", check=False)
            if probe.returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise AssertionError("worker did not accept delegated request")
        docker("network", "disconnect", args.network, client)
        result = execute(client, "agentctl", *cases[1][0], check=False)
        assert result.returncode == 11
        for _ in range(30):
            response = execute(worker, "cat", "/tmp/result", check=False)
            if response.returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise AssertionError("delegated read did not finish")
        delegated = json.loads(response.stdout)
        assert delegated["exit"] == 0 and "data" in json.loads(delegated["body"])
        docker("network", "disconnect", args.network, worker)
        assert execute(worker, "agentctl", *cases[1][0], check=False).returncode == 11
        docker("stop", worker)
        assert execute(worker, "true", check=False).returncode != 0
        passed("direct removal denies requester; previously delegated read continues; worker disconnection and stop revoke delegation")
        assert proxy_before == hashlib.sha256((ROOT / "squid.conf").read_bytes()).hexdigest()
        passed("shared proxy policy unchanged")
        second_interface(args.image, gateway, prefix)
        passed("isolated delivered-image clone: primary-interface read succeeds, secondary interface refuses connection, CONNECT forwarding denied")
        evidence = {"agent_image": json.loads(docker("image", "inspect", args.image).stdout)[0]["Id"],
                    "gateway_image": gateway["Image"], "cli_sha256": actual,
                    "checks": results, "limitations": "ARM64 mock only. No live providers, AMD64, active-request shutdown, or packet-level routing attack proof. Second-interface test uses an isolated clone and two internal bridges, not a live external attachment."}
        if args.output:
            args.output.write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(evidence, indent=2))
    finally:
        for name in reversed(names):
            docker("rm", "-f", "-v", name, check=False)


if __name__ == "__main__":
    main()
