{
  description = "Opt-in Fenced host tools for macOS ARM64 and Linux ARM64/AMD64";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = { self, nixpkgs }:
    let
      systems = [ "aarch64-darwin" "aarch64-linux" "x86_64-linux" ];
      forSystems = nixpkgs.lib.genAttrs systems;
      environment = system:
        let
          pkgs = import nixpkgs { inherit system; };
          lib = pkgs.lib;
          tools = with pkgs; [
            bashInteractive git tmux neovim python3 rsync gnumake docker-client
            openssh coreutils findutils gnused gnugrep gawk
          ];
          toolPath = lib.makeBinPath tools;
          # Keep the legacy install layout, including sibling launchers and hooks.
          # Include only intentional regular files, never a workspace or profile.
          launchers = [
            "run-shell" "story-shell" "meta-shell" "agent-status"
            "agent-vm-status" "agent-docker-usage" "agent-container-stats"
          ];
          regularFiles = dir:
            if builtins.pathExists dir then
              map (name: dir + "/${name}")
                (builtins.attrNames (lib.filterAttrs (_: type: type == "regular")
                  (builtins.readDir dir)))
            else [];
          extraDirs = map (name: ./extras + "/${name}")
            (builtins.attrNames (lib.filterAttrs (_: type: type == "directory")
              (builtins.readDir ./extras)));
          hostCommands = lib.concatMap (dir: regularFiles (dir + "/host-bin")) extraDirs;
          hooks = builtins.filter (path: lib.hasSuffix ".sh" (toString path))
            (lib.concatMap (dir: regularFiles (dir + "/run-shell.d")) extraDirs);
          commands = map (name: ./bin + "/${name}") launchers ++ regularFiles ./host/bin ++ hostCommands;
          names = map builtins.baseNameOf commands;
          hookNames = map builtins.baseNameOf hooks;
          installFile = mode: destination: path: ''
            install -m ${mode} ${lib.escapeShellArg "${path}"} "$out/${destination}/${builtins.baseNameOf path}"
          '';
          launchersPackage = assert builtins.length names == builtins.length (lib.unique names);
            assert builtins.length hookNames == builtins.length (lib.unique hookNames);
            pkgs.stdenvNoCC.mkDerivation {
              pname = "fenced-host-launchers";
              version = "0.1.0";
              dontUnpack = true;
              nativeBuildInputs = [ pkgs.makeWrapper ];
              buildInputs = [ pkgs.bash pkgs.python3 ];
              installPhase = ''
                mkdir -p "$out/bin/run-shell.d" "$out/lib/host-extras"
                ${lib.concatMapStrings (dir: if builtins.pathExists (dir + "/host-profile.json") then "install -m 0644 ${dir}/host-profile.json $out/lib/host-extras/${builtins.baseNameOf dir}.json\n" else "") extraDirs}
                ${lib.concatMapStrings (dir: if builtins.pathExists (dir + "/host-profile.py") then "install -m 0644 ${dir}/host-profile.py $out/lib/host-extras/${builtins.baseNameOf dir}.py\n" else "") extraDirs}
                install -m 0644 ${./host/lib/fenced_services.py} "$out/lib/fenced_services.py"
                install -m 0644 ${./host/lib/fenced-seed.js} "$out/lib/fenced-seed.js"
                ${lib.concatMapStrings (installFile "0755" "bin") commands}
                ${lib.concatMapStrings (installFile "0644" "bin/run-shell.d") hooks}
                patchShebangs "$out/bin"
                for command in ${lib.escapeShellArgs names}; do
                  wrapProgram "$out/bin/$command" --prefix PATH : ${lib.escapeShellArg toolPath}
                done
              '';
            };
          info = pkgs.writeShellScriptBin "fenced-host-info" ''
            set -eu
            printf 'Host tool system: %s\n' ${lib.escapeShellArg system}
            for tool in bash git tmux nvim python3 rsync make docker ssh; do
              printf '%s: %s\n' "$tool" "$(command -v "$tool")"
            done
            bash --version | head -n 1
            git --version
            tmux -V
            nvim --version | head -n 1
            python3 --version
            rsync --version | head -n 1
            make --version | head -n 1
            docker --version
            ssh -V 2>&1
          '';
          shell = pkgs.mkShellNoCC {
            packages = tools ++ [ launchersPackage info ];
            shellHook = ''
              # Run after the caller's interactive startup files; no host mutation.
              export PATH="${launchersPackage}/bin:${info}/bin:${toolPath}:$PATH"
              export FENCED_HOST_SYSTEM=${lib.escapeShellArg system}
            '';
          };
          smoke = pkgs.runCommand "fenced-host-launcher-check" {
            nativeBuildInputs = tools ++ [ launchersPackage ];
          } ''
            run-shell --help >/dev/null
            story-shell --help >/dev/null
            meta-shell --help >/dev/null
            story-setup --help >/dev/null
            agent-status --help >/dev/null
            fenced-doctor --help >/dev/null
            fenced-harness --help >/dev/null
            ${lib.concatMapStrings (path: "test -f ${launchersPackage}/bin/run-shell.d/${builtins.baseNameOf path}\n") hooks}
            touch "$out"
          '';
        in { inherit shell launchersPackage info smoke; };
      environments = forSystems environment;
    in {
      devShells = forSystems (system: {
        default = environments.${system}.shell;
        host = environments.${system}.shell;
      });
      packages = forSystems (system: {
        default = environments.${system}.launchersPackage;
        host-launchers = environments.${system}.launchersPackage;
        host-info = environments.${system}.info;
      });
      checks = forSystems (system: {
        launchers = environments.${system}.smoke;
      });
    };
}
