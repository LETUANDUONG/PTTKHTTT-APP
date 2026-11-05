"""Cosine similarity over normalized CLIP vectors for the small catalogue."""


def rank(query,candidates):
    results=[]
    for product,vector in candidates:
        similarity=sum(a*b for a,b in zip(query,vector))
        results.append({**product,'similarity':round(max(-1,min(1,similarity)),4)})
    return sorted(results,key=lambda p:p['similarity'],reverse=True)
