{ pkgs, ... }:

{
  projectRootFile = "flake.nix";

  programs = {
    nixfmt.enable = true;
    shfmt.enable = true;
    ruff-format.enable = true;
    ruff-check.enable = true;
    mdformat.enable = true;
    taplo.enable = true;
  };

  settings.global.excludes = [
    "**/*.lock"
    "tests/fixtures/**"
  ];
}
