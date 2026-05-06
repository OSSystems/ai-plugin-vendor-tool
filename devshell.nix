{ pkgs, ... }:

pkgs.mkShell {
  name = "ai-plugin-vendor-tool";

  packages = with pkgs; [
    (python3.withPackages (
      ps: with ps; [
        pytest
        mypy
      ]
    ))
    gh
    curl
    jq
    treefmt
    nixfmt
    shfmt
    ruff
    mdformat
    taplo
  ];

  shellHook = ''
    export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
    echo "ai-plugin-vendor-tool devShell — see README.md for commands"
  '';
}
