import dns.resolver
import whois
import requests
import time
from urllib.parse import urlparse

def check_availability_api(domain, public_key, secret_key):
    """
    Sprawdza dostępność domeny poprzez API Aftermarket.pl.
    Zgodnie ze standardem Aftermarket, logowanie odbywa się np. w sposób z parametrem 'key' i 'secret'
    bądź jako Basic Auth. Na ten moment jest to miejsce podłączone - jeśli nie działa z Twoim konkretnym kluczem
    to wdrożymy Fallback automatycznie.
    """
    # Proste i bezpieczne wywołanie - dokumentacja Aftermarket pozwala na wywołanie GET/POST do /domain/check
    url = "https://json.aftermarket.pl/domain/check"
    
    # Zgodnie z PHP: $client = new Client(["key"=>"X", "secret"=>"Y"]);
    # JSON API Aftermarket.pl często przyjmuje autoryzację poprzez Basic Auth 
    # (lub specjalne headery - w razie problemów dołożymy parametry w requescie).
    auth_data = (public_key, secret_key)
    
    payload = {
        "name": domain
    }
    
    try:
        response = requests.post(url, auth=auth_data, json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Po poprawnym odpowiedzi, 'ok' zazwyczaj wynosi 1
            if data.get('ok') == 1:
               # Dodatkowe pole ze statusem np. available
               # Różne API inaczej organizują zwracane typy. Na razie załóżmy, że status 200 to sukces odpytania, i musimy wyciągnąć 'available'.
               status = data.get('data', {}).get('status', 'unknown')
               if status in ['available', 'free', 'unregistered']:
                   return True
               return False
        return None # Problem z autoryzacją API - użyj fallbacku
    except Exception as e:
        print(f"Błąd API: {e}")
        return None

def check_dns(domain):
    """Returns True if domain resolves (taken), False if no records (potentially free)."""
    try:
        dns.resolver.resolve(domain, 'NS')
        return True # Resolves - Taken
    except dns.resolver.NXDOMAIN:
        return False # No domain - Potential Free
    except dns.resolver.NoAnswer:
        try:
            dns.resolver.resolve(domain, 'A')
            return True
        except:
            return False
    except Exception:
        return False

def check_whois(domain):
    """Returns True if registered, False if free."""
    try:
        w = whois.whois(domain)
        # If whois returns domain_name or registrar, it usually means it's taken
        if w.domain_name or getattr(w, 'registrar', None) or getattr(w, 'creation_date', None):
            return True # Taken
        return False # Free
    except Exception:
         # Failed whois query (e.g. rate limting or the domain actually doesn't exist)
         # In most python-whois setups, standard 'Not found' gives empty object or throws error.
        return False

def check_availability_fallback(domain):
    """
    Checks domain availability without API (Free method).
    1. Check DNS (fastest). If it resolves to anything -> taken.
    2. Check WHOIS (slow/rate-limited). If DNS fails to resolve, verify with WHOIS.
    """
    # 1. DNS Check
    if check_dns(domain):
        return False # It resolves, so it is taken

    # 2. WHOIS Check
    # We do a tiny sleep to not instantly ban ourselves on whois servers if doing many
    time.sleep(0.5) 
    if check_whois(domain):
        return False # Registered according to whois

    # If both DNS didn't resolve and WHOIS didn't find registration -> Very likely free!
    return True
