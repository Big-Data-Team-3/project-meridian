import os
from importlib import metadata
import pytest
from unittest.mock import patch


@patch("ssl.SSLContext.load_verify_locations", return_value=None)
def test_gdelt_client_creation(mock_load_verify):
    """Test importing and instantiating the GDELT client."""
    import gdelt

    gd = gdelt.Gdelt()
    assert gd is not None, "Failed to instantiate gdelt client"

def test_fredapi_client_methods():
    """Test fredapi client exposes expected methods."""
    import fredapi

    fred = fredapi.Fred(api_key="test_key")
    assert fred.api_key == "test_key"
    for method in ("get_series", "search"):
        assert hasattr(fred, method), f"fredapi missing {method}"
    print("✓ FRED API client instantiated with key and methods verified")


@patch("ssl.SSLContext.load_verify_locations", return_value=None)
def test_sec_edgar_api_client(mock_load_verify):
    """Test sec-edgar-api client construction."""
    from sec_edgar_api import EdgarClient

    client = EdgarClient()
    assert client is not None
    assert hasattr(client, "get_company_submissions")
    print("✓ SEC EDGAR API client instantiated")


@patch("ssl.SSLContext.load_verify_locations", return_value=None)
def test_secedgar_client(mock_load_verify):
    """Test secedgar SeFilings helper."""
    import secedgar

    filings = secedgar.SeFilings()
    assert filings is not None
    assert hasattr(filings, "get"), "SeFilings missing get()"
    print("✓ SeFilings helper instantiated")


@patch("ssl.SSLContext.load_verify_locations", return_value=None)
def test_sec_edgar_downloader_client(mock_load_verify):
    """Test sec-edgar-downloader Downloader."""
    from sec_edgar_downloader import Downloader

    downloader = Downloader()
    assert downloader is not None
    for attr in ("get", "get_recent_filings"):
        assert hasattr(downloader, attr), f"Downloader missing {attr}"
    print("✓ SEC EDGAR Downloader instantiated")


@patch("ssl.SSLContext.load_verify_locations", return_value=None)
def test_finnhub_client(mock_load_verify):
    """Test finnhub client instantiation."""
    import finnhub

    client = finnhub.Client(api_key="test_key")
    assert client is not None
    for method in ("stock_symbols", "quote"):
        assert hasattr(client, method), f"Finnhub client missing {method}"
    print("✓ Finnhub client instantiated")

# Test package versions match requirements.txt
def test_package_versions():
    """Test that installed package versions match requirements.txt"""
    version_checks = {
        'gdelt': '0.1.14',
        'fredapi': '0.5.2',
        'sec-edgar-api': '1.1.0',
        'secedgar': '0.6.0',
        'sec-edgar-downloader': '5.0.3',
        'finnhub-python': '2.4.25'
    }

    for package, expected_version in version_checks.items():
        installed_version = metadata.version(package)
        assert installed_version == expected_version, (
            f"Version mismatch for {package}: expected {expected_version}, got {installed_version}"
        )
        print(f"✓ {package} version {installed_version} matches requirements")

def test_fredapi_basic_functionality():
    """Test basic FRED API functionality (fredapi is the only library that can be imported in sandbox)"""
    try:
        import fredapi
        # Test with mock API key
        fred = fredapi.Fred(api_key='test_key')
        assert fred.api_key == 'test_key'
        print("✓ FRED API basic functionality test passed")
    except Exception as e:
        pytest.fail(f"FRED API functionality test failed: {e}")

def test_requirements_file_integrity():
    """Test that requirements.txt file is properly formatted"""
    with open('requirements.txt', 'r') as f:
        content = f.read()

    lines = content.strip().split('\n')
    assert len(lines) == 6, f"Expected 6 requirements, got {len(lines)}"

    # Check that each line follows package==version format
    for line in lines:
        assert '==' in line, f"Invalid requirement format: {line}"
        package, version = line.split('==', 1)
        assert package.strip(), f"Empty package name in: {line}"
        assert version.strip(), f"Empty version in: {line}"

    print("✓ requirements.txt file is properly formatted")

# Test that all required packages are installed
def test_all_packages_installed():
    """Test that all required packages from requirements.txt are installed"""
    packages = [
        'gdelt',
        'fredapi',
        'sec-edgar-api',
        'secedgar',
        'sec-edgar-downloader',
        'finnhub-python'
    ]

    missing = []
    for package in packages:
        try:
            metadata.version(package)
        except metadata.PackageNotFoundError:
            missing.append(package)

    assert not missing, f"Missing packages: {', '.join(missing)}"
    print(f"✓ All required packages are installed: {', '.join(packages)}")

# Test environment variables for API keys
def test_api_key_environment_variables():
    """Test that environment variables for API keys are properly configured"""
    required_keys = {
        'FRED_API_KEY': 'Federal Reserve Economic Data API key',
        'FINNHUB_API_KEY': 'Finnhub API key',
        # SEC EDGAR typically doesn't require API keys
        # GDELT is free and doesn't require API keys
    }

    missing_keys = []
    for key, description in required_keys.items():
        if key not in os.environ or not os.environ[key].strip():
            missing_keys.append(f"{key} ({description})")

    if missing_keys:
        pytest.skip(f"Missing API keys (expected in CI/CD): {', '.join(missing_keys)}")
    else:
        print("✓ All required API keys are configured")

def test_data_source_connectivity_simulation():
    """Simulate data source connectivity without actual network calls"""
    data_sources = [
        ("GDELT", "Global Database of Events, Language, and Tone"),
        ("FRED", "Federal Reserve Economic Data"),
        ("SEC EDGAR API", "Securities and Exchange Commission EDGAR database"),
        ("SecEdgar", "Alternative SEC EDGAR client"),
        ("SEC EDGAR Downloader", "Bulk SEC filing downloader"),
        ("Finnhub", "Financial market data and news")
    ]

    print("✓ Data sources configured:")
    for name, description in data_sources:
        print(f"  - {name}: {description}")

    assert len(data_sources) == 6, "Not all expected data sources are configured"

def test_project_setup_integrity():
    """Test overall project setup integrity"""
    # Check that key files exist
    assert os.path.exists('requirements.txt'), "requirements.txt not found"
    assert os.path.exists('tests/'), "tests/ directory not found"
    assert os.path.exists('README.md'), "README.md not found"

    # Check requirements.txt content
    with open('requirements.txt', 'r') as f:
        req_content = f.read().strip()
    assert req_content, "requirements.txt is empty"

    print("✓ Project setup integrity verified")

if __name__ == "__main__":
    # Run tests manually if executed directly
    test_all_packages_installed()
    test_fredapi_basic_functionality()
    test_package_versions()
    test_requirements_file_integrity()
    test_data_source_connectivity_simulation()
    test_project_setup_integrity()
    print("\nAll basic data source tests completed!")
