{ pkgs, inputs, ... }:

# `nix fmt` entry point. Red-tape's formatter module loads `formatter.nix`
# from the project root; it must evaluate to a derivation (the treefmt
# wrapper). We build that wrapper from a treefmt-nix module that registers
# every formatter and linter the project relies on.
inputs.treefmt-nix.lib.mkWrapper pkgs (
  { ... }:
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
)
