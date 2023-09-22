{ lib, buildPythonPackage, setuptools, snowflake-connector-python }:

buildPythonPackage rec {
  pname = "sfconn";
  version = "0.2.5";
  src = ./.;
  format = "pyproject";

  propagatedBuildInputs = [
    snowflake-connector-python
  ];

  nativeBuildInputs = [
    setuptools
  ];

  doCheck = false;

  meta = with lib; {
    homepage = "https://github.com/padhia/sfconn";
    description = "Snowflake connection helper functions";
    maintainers = with maintainers; [ padhia ];
  };
}
