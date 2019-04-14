#!/usr/bin/python3.6
# cid.ninja scraper
# Darkerego, March 2019 ~ xelectron@protonmail.com

import argparse
from selenium import webdriver
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from colorama import init, Fore, Back, Style

import getpass
import stem.connection
import stem.socket
init(autoreset=True)


def printlog(data, outfile):
    print(data)
    with open(outfile, 'a') as log:
        log.write(data + "\n")


def cycle_ident(tor_pass): 
    """

    :param tor_pass: password to authenticate to tor control port
    :return: -- exit upon failure
    """

    try:
        control_socket = stem.socket.ControlPort(port=9051)
    except stem.SocketError as exc:
        print('Unable to connect to port 9051 (%s)' % exc)
        return False

    try:
        stem.connection.authenticate(control_socket)
    except stem.connection.IncorrectSocketType:
        print('Please check in your torrc that 9051 is the ControlPort.')
        print('Maybe you configured it to be the ORPort or SocksPort instead?')
        return False
    except stem.connection.MissingPassword:
        if not tor_pass:
            controller_password = getpass.getpass('Controller password: ')
        else:
            controller_password = tor_pass

        try:
            stem.connection.authenticate_password(control_socket, controller_password)
        except stem.connection.PasswordAuthFailed:
            print('Unable to authenticate, password is incorrect')
            return False
    except stem.connection.AuthenticationFailure as exc:
        print('Unable to authenticate: %s' % exc)
        return False


def query(phone_number, debug, proxy, tor_proxy, outfile):
    """

    :param phone_number: query this number
    :param debug: don't use headless mode (for debugging)
    :param proxy: use this proxy server
    :param tor_proxy: configure browser for tor proxy
    :param outfile: log to this file
    :return: --
    """
    opts = Options()
    if not debug:
        opts.set_headless()
        assert opts.headless  # Operating in headless mode

    profile = webdriver.FirefoxProfile()
    # set FF preference to socks proxy
    if proxy:
        print('Setting proxy...')
        proxy = proxy.split(':')
        proxy_host = proxy[0]
        proxy_port = proxy[1]
        proxy_port = int(proxy_port)
        profile.set_preference("network.proxy.type", 1)
        if not tor_proxy:
            profile.set_preference("network.proxy.http", proxy_host)
            profile.set_preference("network.proxy.http_port", proxy_port)
            profile.set_preference('network.proxy.https', proxy_host)
            profile.set_preference('network.proxy.https', proxy_port)
            profile.set_preference('network.proxy.ssl', proxy_host)
            profile.set_preference('network.proxy.ssl_port', proxy_port)
        profile.set_preference("network.proxy.socks", proxy_host)
        profile.set_preference("network.proxy.socks_port", proxy_port)
        profile.set_preference("network.proxy.socks_version", 5)
        profile.set_preference('network.proxy_dns', 'true')

    profile.update_preferences()
    browser = Firefox(options=opts, firefox_profile=profile)
    get_url = 'https://www.cid.ninja/phone-numbers/?query=#' + str(phone_number)
    browser.get(get_url)

    title = browser.title
    if title == 'Home - CID Ninja':
        print(Fore.RED + 'Maximum lookups for this IP reached, use a new proxy')
        browser.close()
        raise ValueError('IP Blacklist')

    phone_number = browser.find_element_by_id('details-phone-number').text
    printlog('Phone Number: ' + phone_number, outfile)
    details_location = browser.find_element_by_id('details-location').text
    printlog('Location: ' + details_location, outfile)
    cid_name = browser.find_element_by_id('details-cnam').text
    printlog('CID Name: ' + cid_name, outfile)
    carrier_name = browser.find_element_by_id('details-carrier').text
    printlog('Carrier Name: ' + carrier_name, outfile)
    details_sms = browser.find_element_by_id('details-sms').text
    printlog('SMS Email: ' + details_sms, outfile)
    details_old_carrier = browser.find_element_by_id('details-carrier-o').text
    printlog('Old Carrier:' + details_old_carrier, outfile)
    details_mms = browser.find_element_by_id('details-mms').text
    printlog('MMS Email: ' + details_mms, outfile)
    details_tel_num = browser.find_element_by_id('details-tel-num').text
    printlog('Carrier Help Line: ' + details_tel_num, outfile)
    details_slogan = browser.find_element_by_id('details-slogan').text
    printlog('Carrier Slogan: ' + details_slogan, outfile)
    browser.close()


def main():
    """ Program Start
    :return: --
    """

    usage = "usage: ./cidscraper.py -n 8005551212"
    usage += "\nRecommended: Use proxybroker with types HTTP, HTTPS, and SOCKS5 for multiple queries"
    usage += "\n./cidscrape.py -l numbers.lst -p localhost:8888"
    usage += "\n./cidscrape.py -l numbers.lst -t -p localhost:9050 -c 'controllerpassword'"
    parser = argparse.ArgumentParser(usage)
    parser.add_argument('-n', '--phone_number', default='+14158586273', help='Query this number for carrier data',
                        dest='phone_number')
    parser.add_argument('-l', '--list', default=False, dest='phone_number_list', help='List of queries to run')

    parser.add_argument('-d', '--debug', action='store_true', dest='debug', help='Run in non-headless '
                                                                                 'mode for debugging.')
    parser.add_argument('-p', '--proxy', dest='proxy', default=False, help='Use a SOCKS5 proxy '
                                                                           '(proxy broker/tor works nicely) to use. '
                                                                           'Example: localhost:8888')
    parser.add_argument('-t', '--tor_proxy', action='store_true', dest='tor_proxy', default=False,
                        help='Use tor proxy at localhost:9050, enable automatic identity cycling via control port at '
                             'localhost:9150')
    parser.add_argument('-c', '--control_password', dest='tor_pass', help='Password to authenticate tor control port.')
    parser.add_argument('-o', '--outfile', dest='outfile', default='cidscrape.log', help='Log to this file.')

    number_list = []
    args = parser.parse_args()
    phone_number = args.phone_number
    outfile = args.outfile
    if args.tor_proxy:
        print('Using tor proxy. Will automatically request a new identity after each query. Ensure control'
              'port is enabled (localhost:9150) , setting proxy to localhost:9050, override with --proxy')
        tor_proxy = args.tor_proxy
    else:
        tor_proxy = False
    if args.tor_pass:
        tor_pass = args.tor_pass
    else:
        tor_pass = None

    if args.phone_number_list:
        phone_number_list = args.phone_number_list
        print('Reading from %s ' % phone_number_list)
        with open(phone_number_list, 'r') as f:
            f = f.readlines()
            for line in f:
                number_list.append(line)

        read_list = True
    else:
        read_list = False

    debug = args.debug
    if args.proxy and not tor_proxy:
        proxy = args.proxy
    else:
        proxy = False

    if not read_list:
        print(Fore.GREEN + 'Querying %s ... ' % phone_number)
        try:
            query(phone_number, debug, proxy, tor_proxy, outfile)
        except Exception as err:
            print(Fore.RED + 'Error:' + str(err))
        else:
            print(Fore.BLUE + 'Success!')
    else:
        if tor_proxy:
            proxy = 'localhost:9050'
        if proxy:
            print('Using proxy: %s' % proxy)

        print(Fore.YELLOW + 'List mode')

        for n in number_list:
            n = n.rstrip('\n')
            count = 0
            for i in range(3):

                count += 1
                print(Fore.GREEN + 'Querying %s , try: %d' % (n, count))
                # check_proxy(proxy)
                try:
                    query(n, debug, proxy, tor_proxy, outfile)
                except Exception as err:
                    print(Fore.RED + 'Error: ' + str(err))
                    if tor_proxy:
                        print(Fore.BLUE + 'Cycling tor identity ...')
                        try:
                            cycle_ident(tor_pass)
                        except:
                            pass

                else:
                    print(Fore.BLUE + 'Success!')
                    if tor_proxy:
                        print(Fore.BLUE + 'Cycling tor identity ...')
                        try:
                            cycle_ident(tor_pass)
                        except:
                            pass
                    break


if __name__ == '__main__':
    main()
