"""Unit tests for nmap XML parser and NmapExecutor.

All tests run without Docker — sandbox calls are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from oxpwn.core.models import ToolResult
from oxpwn.sandbox.tools.nmap import NmapExecutor, parse_nmap_xml

# ---------------------------------------------------------------------------
# Realistic nmap XML fixtures
# ---------------------------------------------------------------------------

NMAP_XML_TYPICAL = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -sV -oX - 192.168.1.0/30" start="1700000000">
  <host starttime="1700000001" endtime="1700000010">
    <status state="up" reason="syn-ack"/>
    <address addr="192.168.1.1" addrtype="ipv4"/>
    <hostnames>
      <hostname name="gateway.local" type="PTR"/>
    </hostnames>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open" reason="syn-ack"/>
        <service name="ssh" product="OpenSSH" version="8.9p1"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="open" reason="syn-ack"/>
        <service name="http" product="nginx" version="1.24.0"/>
      </port>
      <port protocol="tcp" portid="443">
        <state state="closed" reason="reset"/>
        <service name="https"/>
      </port>
    </ports>
  </host>
  <host starttime="1700000001" endtime="1700000010">
    <status state="up" reason="syn-ack"/>
    <address addr="192.168.1.2" addrtype="ipv4"/>
    <hostnames/>
    <ports>
      <port protocol="tcp" portid="3306">
        <state state="open" reason="syn-ack"/>
        <service name="mysql" product="MySQL" version="8.0.35"/>
      </port>
    </ports>
  </host>
  <runstats><finished time="1700000020"/></runstats>
</nmaprun>
"""

NMAP_XML_EMPTY = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -sV -oX - 10.0.0.0/30" start="1700000000">
  <runstats><finished time="1700000005"/></runstats>
</nmaprun>
"""

NMAP_XML_HOST_NO_PORTS = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -sV -oX - 10.0.0.1" start="1700000000">
  <host starttime="1700000001" endtime="1700000003">
    <status state="up" reason="arp-response"/>
    <address addr="10.0.0.1" addrtype="ipv4"/>
    <hostnames/>
  </host>
  <runstats><finished time="1700000005"/></runstats>
</nmaprun>
"""

NMAP_XML_WITH_SCRIPTS = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -sV --script=http-title,ssl-cert -oX - 10.0.0.1" start="1700000000">
  <host starttime="1700000001" endtime="1700000010">
    <status state="up" reason="syn-ack"/>
    <address addr="10.0.0.1" addrtype="ipv4"/>
    <hostnames/>
    <ports>
      <port protocol="tcp" portid="80">
        <state state="open" reason="syn-ack"/>
        <service name="http" product="Apache" version="2.4.57"/>
        <script id="http-title" output="Welcome to ACME Corp"/>
      </port>
      <port protocol="tcp" portid="443">
        <state state="open" reason="syn-ack"/>
        <service name="https" product="Apache" version="2.4.57"/>
        <script id="ssl-cert" output="Subject: CN=acme.com; Issuer: Let's Encrypt"/>
        <script id="http-title" output="ACME Corp Portal"/>
      </port>
    </ports>
  </host>
  <runstats><finished time="1700000020"/></runstats>
</nmaprun>
"""

NMAP_XML_NON_UTF8 = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -sV -oX - 10.0.0.1" start="1700000000">
  <host starttime="1700000001" endtime="1700000010">
    <status state="up" reason="syn-ack"/>
    <address addr="10.0.0.1" addrtype="ipv4"/>
    <hostnames/>
    <ports>
      <port protocol="tcp" portid="21">
        <state state="open" reason="syn-ack"/>
        <service name="ftp" product="vsftpd" version="3.0.5"/>
        <script id="banner" output="220 Welcome \ufffd\ufffd FTP Server"/>
      </port>
    </ports>
  </host>
  <runstats><finished time="1700000020"/></runstats>
</nmaprun>
"""


# ---------------------------------------------------------------------------
# parse_nmap_xml tests
# ---------------------------------------------------------------------------


class TestParseNmapXml:
    """Unit tests for parse_nmap_xml()."""

    def test_typical_scan_two_hosts(self) -> None:
        """Parse typical scan with 2 hosts and multiple ports/services."""
        result = parse_nmap_xml(NMAP_XML_TYPICAL)
        hosts = result["hosts"]

        assert len(hosts) == 2

        # First host
        h1 = hosts[0]
        assert h1["address"] == "192.168.1.1"
        assert h1["hostnames"] == ["gateway.local"]
        assert h1["status"] == "up"
        assert len(h1["ports"]) == 3

        # Port 22 — open SSH
        p22 = h1["ports"][0]
        assert p22["port_id"] == 22
        assert p22["protocol"] == "tcp"
        assert p22["state"] == "open"
        assert p22["service_name"] == "ssh"
        assert p22["service_product"] == "OpenSSH"
        assert p22["service_version"] == "8.9p1"

        # Port 80 — open HTTP
        p80 = h1["ports"][1]
        assert p80["port_id"] == 80
        assert p80["service_name"] == "http"
        assert p80["service_product"] == "nginx"

        # Port 443 — closed
        p443 = h1["ports"][2]
        assert p443["state"] == "closed"

        # Second host
        h2 = hosts[1]
        assert h2["address"] == "192.168.1.2"
        assert h2["hostnames"] == []
        assert len(h2["ports"]) == 1
        assert h2["ports"][0]["service_name"] == "mysql"

    def test_empty_scan_no_hosts(self) -> None:
        """Empty scan (0 hosts up) returns empty hosts list."""
        result = parse_nmap_xml(NMAP_XML_EMPTY)
        assert result["hosts"] == []

    def test_host_no_open_ports(self) -> None:
        """Host present but no ports section — ports list empty."""
        result = parse_nmap_xml(NMAP_XML_HOST_NO_PORTS)
        hosts = result["hosts"]

        assert len(hosts) == 1
        assert hosts[0]["address"] == "10.0.0.1"
        assert hosts[0]["status"] == "up"
        assert hosts[0]["ports"] == []

    def test_scripts_extracted(self) -> None:
        """Script output is extracted with id and output fields."""
        result = parse_nmap_xml(NMAP_XML_WITH_SCRIPTS)
        hosts = result["hosts"]
        assert len(hosts) == 1

        port80 = hosts[0]["ports"][0]
        assert len(port80["scripts"]) == 1
        assert port80["scripts"][0]["id"] == "http-title"
        assert port80["scripts"][0]["output"] == "Welcome to ACME Corp"

        port443 = hosts[0]["ports"][1]
        assert len(port443["scripts"]) == 2
        script_ids = {s["id"] for s in port443["scripts"]}
        assert script_ids == {"ssl-cert", "http-title"}

    def test_non_utf8_characters(self) -> None:
        """Non-UTF-8 replacement characters in banner do not crash parser."""
        result = parse_nmap_xml(NMAP_XML_NON_UTF8)
        hosts = result["hosts"]
        assert len(hosts) == 1

        port21 = hosts[0]["ports"][0]
        assert port21["service_name"] == "ftp"
        # Replacement chars present in script output — no crash
        assert "\ufffd" in port21["scripts"][0]["output"]

    def test_returns_dict_with_hosts_key(self) -> None:
        """All results have a top-level 'hosts' key."""
        for xml in (NMAP_XML_TYPICAL, NMAP_XML_EMPTY, NMAP_XML_HOST_NO_PORTS):
            result = parse_nmap_xml(xml)
            assert "hosts" in result


# ---------------------------------------------------------------------------
# NmapExecutor tests (mocked sandbox)
# ---------------------------------------------------------------------------


class TestNmapExecutor:
    """Unit tests for NmapExecutor with mocked DockerSandbox."""

    @pytest.fixture()
    def mock_sandbox(self) -> MagicMock:
        """Return a mock DockerSandbox with async execute()."""
        sandbox = MagicMock()
        sandbox.execute = AsyncMock(
            return_value=ToolResult(
                tool_name="sandbox",
                command="nmap -sV -oX - 192.168.1.1",
                stdout=NMAP_XML_TYPICAL,
                stderr="",
                exit_code=0,
                duration_ms=4500,
            )
        )
        return sandbox

    async def test_run_default_flags(self, mock_sandbox: MagicMock) -> None:
        """run() builds correct command with default flags."""
        executor = NmapExecutor(mock_sandbox)
        result = await executor.run("192.168.1.1")

        mock_sandbox.execute.assert_called_once_with(
            "nmap -sV -oX - 192.168.1.1"
        )
        assert result.tool_name == "nmap"
        assert result.parsed_output is not None
        assert len(result.parsed_output["hosts"]) == 2

    async def test_run_with_ports(self, mock_sandbox: MagicMock) -> None:
        """run() includes -p flag when ports are specified."""
        executor = NmapExecutor(mock_sandbox)
        await executor.run("10.0.0.1", ports="80,443")

        cmd = mock_sandbox.execute.call_args[0][0]
        assert "-p 80,443" in cmd
        assert cmd.endswith("10.0.0.1")

    async def test_run_custom_flags(self, mock_sandbox: MagicMock) -> None:
        """run() uses custom flags when provided."""
        executor = NmapExecutor(mock_sandbox)
        await executor.run("10.0.0.1", flags="-sS -T4")

        cmd = mock_sandbox.execute.call_args[0][0]
        assert cmd.startswith("nmap -sS -T4 -oX -")

    async def test_run_xml_parse_failure(self, mock_sandbox: MagicMock) -> None:
        """When stdout is not valid XML, parsed_output is None."""
        mock_sandbox.execute.return_value = ToolResult(
            tool_name="sandbox",
            command="nmap -sV -oX - bad",
            stdout="Starting Nmap 7.94 -- ERROR: host not found",
            stderr="",
            exit_code=1,
            duration_ms=100,
        )

        executor = NmapExecutor(mock_sandbox)
        result = await executor.run("bad")

        assert result.parsed_output is None
        assert result.exit_code == 1
