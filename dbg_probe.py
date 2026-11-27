import sources
g=sources._get
B="https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/"
print("AUCT", g(B+"auctions_query?sort=-auction_date&page[size]=3&fields=auction_date,security_type,security_term,high_yield,bid_to_cover_ratio")[:700])
print("UPCOMING", g(B+"upcoming_auctions?sort=-auction_date&page[size]=5")[:700])
