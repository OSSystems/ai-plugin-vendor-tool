{ pkgs, inputs, ... }:

let
  formatter = import ./formatter.nix { inherit pkgs inputs; };
in
pkgs.mkShell {
  name = "ai-plugin-vendor-tool";

  packages =
    (with pkgs; [
      (python3.withPackages (
        ps: with ps; [
          pytest
        ]
      ))
      pyright
      gh
      curl
      jq
      nixfmt
      shfmt
      ruff
      mdformat
      taplo
    ])
    ++ [ formatter ];

  shellHook = ''
    export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
    echo "ai-plugin-vendor-tool devShell — see README.md for commands"
  '';
}
