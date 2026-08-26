# -*- coding: utf-8 -*-
"""Probe Europe PMC records for RSC papers 02/13/16 and ACS 08/15/17, AIP 18, Wiley 20."""
import requests

dois = {
    "13": "10.1039/D5LC00634A",
    "16": "10.1039/D5DD00345H",
    "08": "10.1021/acsomega.5c06253",
    "15": "10.1021/acssensors.4c03621",
    "17": "10.1021/acssensors.5c02031",
    "18": "10.1063/5.0159981",
    "20": "10.1002/smll.73821",
}
for k, d in dois.items():
    r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                     params={"query": f'DOI:"{d}"', "format": "json", "resultType": "core"},
                     headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"}, timeout=30)
    print("===", k, d, r.status_code)
    for rec in r.json().get("resultList", {}).get("result", []):
        print("  pmcid", rec.get("pmcid"), "pmid", rec.get("pmid"), "OA", rec.get("isOpenAccess"), rec.get("pubYear"))
        print("  title", (rec.get("title") or "")[:90])
        print("  ft", [u.get("url") for u in rec.get("fullTextUrlList", {}).get("fullTextUrl", [])])
