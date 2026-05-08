{ pkgs, inputs, ... }:

# `nix fmt` entry point. Red-tape's formatter module loads `formatter.nix`
# from the project root; it must evaluate to a derivation (the treefmt
# wrapper). We build that wrapper from a treefmt-nix module that registers
# every formatter, linter, and type checker the project relies on.
let
  pyrightPython = pkgs.python3.withPackages (ps: with ps; [ pytest ]);
in
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
      # Pyright auto-loads `[tool.pyright]` from pyproject.toml. `--pythonpath`
      # points at a python env that includes pytest so test imports resolve.
      pyright = {
        enable = true;
        directories."" = {
          options = [
            "--pythonpath"
            "${pyrightPython}/bin/python"
          ];
          modules = [
            "src"
            "tests"
          ];
        };
      };
    };

    settings.global.excludes = [
      "**/*.lock"
      "tests/fixtures/**"
    ];
  }
)
