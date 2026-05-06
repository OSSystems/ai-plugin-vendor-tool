{
  pkgs,
  lib,
  pname,
  ...
}:
let
  python = pkgs.python3.withPackages (ps: with ps; [ pytest ]);
  src = lib.fileset.toSource {
    root = ../.;
    fileset = lib.fileset.unions [
      ../src
      ../tests
      ../pyproject.toml
    ];
  };
in
pkgs.runCommandLocal pname { nativeBuildInputs = [ python ]; } ''
  cp -r ${src}/. .
  export HOME=$(mktemp -d)
  pytest -ra
  touch $out
''
