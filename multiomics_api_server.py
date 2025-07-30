
from fastapi import FastAPI, Query
from typing import List
import httpx

app = FastAPI(title="MultiOmics Data API", description="Unified API for KEGG, Ensembl, UniProt, and PubMed")

@app.get("/gene/pathways")
async def get_kegg_pathways(gene_ids: List[str] = Query(...)):
    results = {}
    async with httpx.AsyncClient() as client:
        for gene_id in gene_ids:
            url = f"https://rest.kegg.jp/link/pathway/{gene_id}"
            resp = await client.get(url)
            results[gene_id] = resp.text.strip().splitlines()
    return results

@app.get("/gene/info")
async def get_ensembl_info(gene_symbols: List[str], species: str = "homo_sapiens"):
    results = {}
    async with httpx.AsyncClient() as client:
        for symbol in gene_symbols:
            url = f"https://rest.ensembl.org/lookup/symbol/{species}/{symbol}?content-type=application/json"
            resp = await client.get(url)
            results[symbol] = resp.json()
    return results

@app.get("/protein/info")
async def get_uniprot_info(accession_ids: List[str]):
    results = {}
    async with httpx.AsyncClient() as client:
        for acc in accession_ids:
            url = f"https://rest.uniprot.org/uniprotkb/{acc}.json"
            resp = await client.get(url)
            results[acc] = resp.json()
    return results

@app.get("/pubmed/search")
async def search_pubmed(query: str, max_results: int = 5):
    async with httpx.AsyncClient() as client:
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": max_results}
        search_resp = await client.get(search_url, params=search_params)
        ids = search_resp.json()["esearchresult"]["idlist"]
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        fetch_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
        fetch_resp = await client.get(fetch_url, params=fetch_params)
        summaries = fetch_resp.json()["result"]
        return {pid: summaries[pid] for pid in ids if pid in summaries}

from fastapi import Body

@app.post("/gene/all")
async def get_all_sources(gene_symbols: List[str], species: str = "homo_sapiens"):
    combined_results = {}
    async with httpx.AsyncClient() as client:
        for symbol in gene_symbols:
            gene_result = {}
            ensembl_url = f"https://rest.ensembl.org/lookup/symbol/{species}/{symbol}?content-type=application/json"
            ensembl_resp = await client.get(ensembl_url)
            gene_result["ensembl"] = ensembl_resp.json()
            gene_id = f"hsa:{symbol}"
            kegg_url = f"https://rest.kegg.jp/link/pathway/{gene_id}"
            kegg_resp = await client.get(kegg_url)
            gene_result["kegg_pathways"] = kegg_resp.text.strip().splitlines()
            uni_url = f"https://rest.uniprot.org/uniprotkb/search?query=gene_exact:{symbol}+AND+organism_id:9606&format=json&fields=accession"
            uni_resp = await client.get(uni_url)
            uniprot_ids = uni_resp.json().get("results", [])
            if uniprot_ids:
                acc_id = uniprot_ids[0]["primaryAccession"]
                acc_info_url = f"https://rest.uniprot.org/uniprotkb/{acc_id}.json"
                acc_resp = await client.get(acc_info_url)
                gene_result["uniprot"] = acc_resp.json()
            pubmed_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            pubmed_params = {"db": "pubmed", "term": f"{symbol}[gene] AND Homo sapiens[orgn]", "retmode": "json", "retmax": 5}
            pubmed_resp = await client.get(pubmed_url, params=pubmed_params)
            gene_result["pubmed_ids"] = pubmed_resp.json()["esearchresult"]["idlist"]
            combined_results[symbol] = gene_result
    return combined_results
