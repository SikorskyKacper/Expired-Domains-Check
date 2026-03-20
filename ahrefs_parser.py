import pandas as pd
import tldextract

def extract_domain(url):
    """Extahuje root domenę z dowolnego ciągu URL lub stringa."""
    if not isinstance(url, str):
        return None
    
    # Tldextract requires scheme to reliably parse sometimes, but can also work without it
    if not url.startswith('http'):
        url_to_extract = 'http://' + url
    else:
        url_to_extract = url
        
    ext = tldextract.extract(url_to_extract)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}".lower()
    return None

def parse_ahrefs_file(file_obj):
    """
    Czyta plik (CSV lub XLSX) od Ahrefs.
    Zwraca DataFrame zawierający kolumny: Root Domain, DR, Traffic (Posortowane i zgrupowane).
    """
    file_name = file_obj.name.lower()
    
    if file_name.endswith('.csv'):
        # Ahrefs exports can be UTF-8 or UTF-16, and use various separators
        encodings_to_try = [('utf-8', ','), ('utf-8', ';'), ('utf-8', '\t'), 
                            ('utf-16', '\t'), ('utf-16', ','), ('utf-16', ';')]
        
        df = None
        for enc, sep in encodings_to_try:
            try:
                file_obj.seek(0)
                temp_df = pd.read_csv(file_obj, encoding=enc, sep=sep, on_bad_lines='skip')
                if len(temp_df.columns) > 1:
                    df = temp_df
                    break
            except Exception:
                continue
                
        if df is None:
            # Fallback to default if all failed (might actually be 1 column)
            file_obj.seek(0)
            try:
                df = pd.read_csv(file_obj, encoding='utf-8')
            except Exception:
                file_obj.seek(0)
                df = pd.read_csv(file_obj, encoding='utf-16', sep='\t')
    elif file_name.endswith('.xlsx'):
        df = pd.read_excel(file_obj)
    else:
        raise ValueError("Nieobsługiwany format pliku. Proszę wrzucić plik CSV lub XLSX.")
        
    # Standardize column names mapping lower-cased and stripped to original
    cols_map = {str(c).strip().lower(): c for c in df.columns}
    
    url_col = None
    dr_col = None
    traffic_col = None
    
    # Znajdź kolumnę URL
    for c in cols_map:
        if ('link' in c and 'url' in c) or ('domain' in c and 'rating' not in c and 'traffic' not in c):
            url_col = cols_map[c]
            break
            
    # Znajdź kolumnę DR
    for c in cols_map:
        if 'dr' in c or 'domain rating' in c:
            dr_col = cols_map[c]
            break
            
    # Znajdź kolumnę Traffic
    for c in cols_map:
        if 'traffic' in c:
             traffic_col = cols_map[c]
             break

    if not url_col:
        # Fallback jeśli kolumny mają dziwne nazwy: bierzemy pierwszą, co ma w sobie HTTP/URL
        for col in df.columns:
            if df[col].astype(str).str.contains('http', na=False).any() or df[col].astype(str).str.contains('\.', na=False).any():
                url_col = col
                break
                
    if not url_col:
        raise ValueError("Nie mogłem odnaleźć w pliku kolumny z adresami URL/Domeną. Upewnij się, że to poprawny eksport.")

    # Apply extraction
    df['Root Domain'] = df[url_col].apply(extract_domain)
    clean_df = df.dropna(subset=['Root Domain']).copy()
    
    dr_out_col = 'DR'
    traffic_out_col = 'Traffic'
    
    # Cast params to numeric
    if dr_col:
        clean_df[dr_out_col] = pd.to_numeric(clean_df[dr_col], errors='coerce').fillna(0)
    else:
         clean_df[dr_out_col] = 0.0
         
    if traffic_col:
        clean_df[traffic_out_col] = pd.to_numeric(clean_df[traffic_col], errors='coerce').fillna(0)
    else:
         clean_df[traffic_out_col] = 0.0

    # Groupby domain to get the max DR/Traffic (since one domain can have many outgoing links)
    aggregated = clean_df.groupby('Root Domain').agg({
        dr_out_col: 'max',
        traffic_out_col: 'max'
    }).reset_index()
    
    # Sort initially
    aggregated = aggregated.sort_values(by=[dr_out_col, traffic_out_col], ascending=[False, False])
    
    return aggregated
