from fastapi import Request

@app.post("/gene/all")
async def get_all_sources_flexible(request: Request):
    body = await request.json()
    
    # Accept plain list of strings
    if isinstance(body, list):
        gene_symbols = body
        species = "homo_sapiens"
    elif isinstance(body, dict):
        gene_symbols = body.get("gene_symbols", [])
        species = body.get("species", "homo_sapiens")
    else:
        return {"error": "Invalid format. Send either an array or an object."}

    combined_results = {}
    async with httpx.AsyncClient() as client:
        for symbol in gene_symbols:
            gene_result = {}

            ensembl_url = f"https://rest.ensembl.org/lookup/symbol/{species}/{symbol}?content-type=application/json"
            ensembl_resp = await client.get(ensembl_url)
            gene_result["ensembl"] = ensembl_resp.json()

            gene_id = f"hsa:{symbol}" if species == "homo_sapiens" else f"sly:{symbol}"
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
