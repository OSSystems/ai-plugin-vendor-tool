{
  description = "ai-plugin-vendor-tool — vendor Claude Code plugin skills from upstream GitHub repos";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    red-tape.url = "github:phaer/red-tape";
    red-tape.inputs.nixpkgs.follows = "nixpkgs";

    # Pinned to https://github.com/numtide/treefmt-nix/pull/504 (pyright module)
    # so we can drop the manual `settings.formatter.pyright` block in
    # formatter.nix. Switch back to numtide/treefmt-nix once the PR is merged.
    treefmt-nix.url = "github:otavio/treefmt-nix/pyright-init";
    treefmt-nix.inputs.nixpkgs.follows = "nixpkgs";

    nix-github-actions.url = "github:nix-community/nix-github-actions";
    nix-github-actions.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    inputs:
    let
      base = inputs.red-tape.mkFlake {
        inherit inputs;
        src = ./.;
      };
    in
    base
    // {
      githubActions = inputs.nix-github-actions.lib.mkGithubMatrix {
        checks = { inherit (base.checks) x86_64-linux; };
      };
    };
}
