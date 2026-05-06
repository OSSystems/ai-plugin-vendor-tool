{
  description = "ai-plugin-vendor-tool — vendor Claude Code plugin skills from upstream GitHub repos";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    red-tape.url = "github:phaer/red-tape";
    red-tape.inputs.nixpkgs.follows = "nixpkgs";

    treefmt-nix.url = "github:numtide/treefmt-nix";
    treefmt-nix.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    inputs:
    inputs.red-tape.mkFlake {
      inherit inputs;
      src = ./.;
    };
}
