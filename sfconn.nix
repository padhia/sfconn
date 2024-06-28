{
  lib,
  buildPythonPackage,
  setuptools,
  snowflake-connector-python,
  pyjwt,
  pytest
}:
buildPythonPackage rec {
  pname     = "sfconn";
  version   = "0.3.2";
  pyproject = true;
  src       = ./.;

  propagatedBuildInputs = [ snowflake-connector-python pyjwt ];
  nativeBuildInputs     = [ setuptools pytest ];
  doCheck               = false;

  meta = with lib; {
    homepage    = "https://github.com/padhia/sfconn";
    description = "Snowflake connection helper functions";
    maintainers = with maintainers; [ padhia ];
  };
}
