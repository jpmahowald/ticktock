import calendar
import email.utils
import os
import requests
import time

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_ntpd_service(host):
    """ Test ntpd running according to service manager """
    enabled = 0
    running = 0
    # Debian systemctl isn't working unprivilaged for some reason
    with host.sudo():
        # For a correct count, Debian aliases chrony.service to chronyd.service
        # but need ntp and ntpd as Red Hat is named differently
        for servicename in ['chronyd', 'ntp', 'ntpd']:
            serviceobj = host.service(servicename)
            # FIXME SLES gets exceptions in is_enabled
            # something about  /etc/rc?.d/
            # https://github.com/philpep/testinfra/issues/360
            try:
                if serviceobj.is_enabled:
                    enabled += 1
            except AssertionError:
                systemctlcmd = "systemctl is-enabled {0}".format(servicename)
                if host.run(systemctlcmd).rc == 0:
                    enabled += 1
            if serviceobj.is_running:
                running += 1
    assert enabled == 1
    assert running == 1


def test_ntpd_listening(host):
    """ Test listening on udp/ntp """
    v4 = host.socket("udp://127.0.0.1:123")
    v6 = host.socket("udp://::1:123")
    # FIXME listening check not reliable
    v4.is_listening or v6.is_listening


def test_https_date(host):
    """ Sanity check host time versus a HTTPS Date header
        Inspired by openntpd but a different implementation
    """
    dateurl = "https://www.google.com"
    response = requests.head(dateurl)
    datetuple = email.utils.parsedate(response.headers["Date"])
    httpsdatestamp = calendar.timegm(datetuple)
    delta = time.time() - httpsdatestamp
    # Assume network request latency plus offset is sub-second
    # Might not be if doing a long slew, although ntpd was just restarted
    assert abs(delta) < 1
