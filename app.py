import streamlit as st
import pandas as pd
from ahrefs_parser import parse_ahrefs_file
from domain_checker import check_availability_api, check_availability_fallback
import time

# Konfiguracja strony
st.set_page_config(page_title="Domain Hunter", page_icon="🎯", layout="wide")

st.title("🎯 Wyszukiwarka Wygasłych Domen SEO")
st.markdown("Wgraj swój plik z linkami wychodzącymi (eksport z Ahrefs), a ja znajdę te domeny, które mają wysokie parametry DR/Traffic i są wolne do przejęcia! Wyniki pojawią się bezpośrednio poniżej.")

# Boczny panel ustawień
with st.sidebar:
    st.header("⚙️ Opcje API (Aftermarket.pl)")
    st.info("Podanie API Aftermarket znacznie przyśpiesza sprawdzanie. Jeśli nie masz kluczy, aplikacja użyje darmowej (nieco wolniejszej) metody WHOIS/DNS.")
    use_api = st.checkbox("Użyj Aftermarket API")
    pub_key = st.text_input("Klucz publiczny (Key)", type="password", disabled=not use_api)
    sec_key = st.text_input("Klucz prywatny (Secret)", type="password", disabled=not use_api)
    
    st.markdown("---")
    max_check = st.number_input("Maksymalna ilość domen do sprawdzenia", min_value=1, max_value=5000, value=100)
    st.caption("Pamiętaj, że sprawdzanie bez API dla setek domen może zająć trochę czasu.")

# Główna sekcja Wrzucania Pliku
uploaded_file = st.file_uploader("📥 Przeciągnij i upuść plik z Ahrefs (CSV lub XLSX)", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        with st.spinner("Przetwarzanie pliku danych..."):
            domains_df = parse_ahrefs_file(uploaded_file)
            
            # Limit domains to speed up UI
            domains_df = domains_df.head(int(max_check))
            st.success(f"Znalazłem {len(domains_df)} unikalnych domen (po złączeniu duplikatów). Domeny posortowano po parametrach DR i Traffic.")
            
        with st.expander("👀 Podgląd wszystkich zaimportowanych domen (Przed sprawdzeniem)"):
             st.dataframe(domains_df, use_container_width=True)

        st.markdown("### 🔍 Wyniki - Wolne Domeny")
        st.write("W tej tabeli będą pojawiać się **wyłącznie wolne domeny** na żywo podczas sprawdzania!")
        
        # Interaktywna tabela na wyniki
        results_placeholder = st.empty()
        
        if st.button("🚀 Uruchom Sprawdzanie", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            free_domains = []
            total = len(domains_df)
            
            # Wpierw wrzucamy puste, aby wymusić UI
            results_placeholder.dataframe(pd.DataFrame(columns=["Domena", "DR", "Traffic"]), use_container_width=True)

            for index, row in domains_df.iterrows():
                domain = row['Root Domain']
                dr = row['DR']
                traffic = row['Traffic']
                
                status_text.markdown(f"**Sprawdzanie ({index+1}/{total}):** `{domain}` ...")
                
                is_free = False
                if use_api and pub_key and sec_key:
                    res = check_availability_api(domain, pub_key, sec_key)
                    if res is not None:
                        is_free = res
                    else:
                        # Fallback when API misconfigured
                         is_free = check_availability_fallback(domain)
                else:
                     is_free = check_availability_fallback(domain)
                     
                if is_free:
                     free_domains.append({
                         "Domena": domain,
                         "DR": dr,
                         "Traffic": traffic,
                         "Dostępność": "✅ Wolna"
                     })
                     # Aktualizujemy tabelę na żywo!
                     # Wyświetla dane w aplikacji bez konieczności pobierania
                     live_df = pd.DataFrame(free_domains)
                     live_df = live_df.sort_values(by=['DR', 'Traffic'], ascending=[False, False])
                     results_placeholder.dataframe(live_df, use_container_width=True)
                     
                progress_bar.progress((index+1)/total)
                
            status_text.success("✅ Sprawdzanie zakończone!")
            progress_bar.empty()
            
            if len(free_domains) > 0:
                st.balloons()
                final_df = pd.DataFrame(free_domains).sort_values(by=['DR', 'Traffic'], ascending=[False, False])
                # Wyniki są wpisane w results_placeholder stale, więc dodajemy tylko przycisk pobierania na koniec:
                st.markdown("---")
                csv_data = final_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                     label="💾 Zapisz wolne domeny jako plik CSV",
                     data=csv_data,
                     file_name="zlapane_wygasle_domeny.csv",
                     mime="text/csv"
                )
            else:
                st.warning("Przykro mi, nie znaleziono żadnej wolnej domeny wśród tej listy 😞")

    except Exception as e:
        st.error(f"Wystąpił błąd podczas analizy: {str(e)}")
