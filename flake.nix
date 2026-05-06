{
  description = "ai-plugin-vendor-tool — vendor Claude Code plugin skills from upstream GitHub repos";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    red-tape.url = "github:phaer/red-tape";
    red-tape.inputs.nixpkgs.follows = "nixpkgs";

    treefmt-nix.url = "github:numtide/treefmt-nix";
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
