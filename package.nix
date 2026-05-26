{ pkgs, lib, ... }:
pkgs.python3Packages.buildPythonApplication {
  pname = "ai-plugin-vendor-tool";
  version = "0.2.0";
  pyproject = true;

  src = lib.fileset.toSource {
    root = ./.;
    fileset = lib.fileset.unions [
      ./src
      ./pyproject.toml
      ./README.md
    ];
  };

  build-system = [ pkgs.python3Packages.setuptools ];

  nativeBuildInputs = [ pkgs.makeBinaryWrapper ];

  # Tests run as their own flake check; skip here so a package build doesn't
  # need the test fixtures.
  doCheck = false;

  postFixup = ''
    wrapProgram $out/bin/ai-plugin-vendor-tool \
      --prefix PATH : ${lib.makeBinPath [ pkgs.gh ]}
  '';

  meta = {
    description = "Vendor third-party Claude Code skills from upstream GitHub repos";
    homepage = "https://github.com/OSSystems/ai-plugin-vendor-tool";
    license = lib.licenses.asl20;
    mainProgram = "ai-plugin-vendor-tool";
    platforms = lib.platforms.unix;
  };
}
