{
  lib,
  buildPythonPackage,
  fetchPypi,
  setuptools,
  snowflake-connector-python,
  pyjwt,
  pytest
}:
buildPythonPackage rec {
  pname     = "sfconn";
  version   = "0.2.5";
  pyproject = true;

  src = fetchPypi {
    inherit pname version;
    hash = "sha256-jdhR9UgHH2klrTtI0bSWN4/FSYXxJdlDhKMRW7c+AdQ=";
  };

  propagatedBuildInputs = [ snowflake-connector-python pyjwt ];
  nativeBuildInputs     = [ setuptools pytest ];
  doCheck               = false;

  meta = with lib; {
    homepage    = "https://github.com/padhia/sfconn";
    description = "Snowflake connection helper functions";
    maintainers = with maintainers; [ padhia ];
  };
}
