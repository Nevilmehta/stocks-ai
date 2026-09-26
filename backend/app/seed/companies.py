"""Company reference data (symbol, name, sector, description) for the 16 seeded
Indian large-caps - real companies, real descriptions. Price history and
financials/ratios are what's synthetic/real depending on MARKET_DATA_PROVIDER
(see app/config.py and the frontend's DEMO DATA badge); this file itself is
just company identity/profile data, not market data.
"""

DEMO_COMPANIES: list[dict] = [
    {
        "symbol": "RELIANCE",
        "name": "Reliance Industries Ltd",
        "exchange": "NSE",
        "sector": "Energy",
        "industry": "Refineries & Petrochemicals",
        "description": (
            "Reliance Industries is India's largest private-sector conglomerate by revenue and market "
            "capitalisation, built around three core engines: its oil-to-chemicals business anchored by "
            "the Jamnagar refinery complex, one of the largest and most complex refining sites in the "
            "world; Reliance Retail, India's biggest retailer with a nationwide store network and "
            "e-commerce presence; and Reliance Jio, the telecom operator that triggered a data-price "
            "revolution in India and now serves hundreds of millions of subscribers. Founded by "
            "Dhirubhai Ambani and led today by Mukesh Ambani, the group has repeatedly ranked among the "
            "most valuable listed companies on Indian exchanges."
        ),
    },
    {
        "symbol": "TCS",
        "name": "Tata Consultancy Services Ltd",
        "exchange": "NSE",
        "sector": "Information Technology",
        "industry": "IT Services & Consulting",
        "description": (
            "Tata Consultancy Services is India's largest IT services company by revenue and market "
            "capitalisation, and part of the Tata Group. It provides consulting, technology, and "
            "business-process outsourcing services to clients across banking, insurance, retail, "
            "manufacturing, and telecom, with operations spanning more than 55 countries and a "
            "workforce of several hundred thousand employees. TCS is known for consistently strong "
            "operating margins and long-running relationships with many of the world's largest "
            "enterprises."
        ),
    },
    {
        "symbol": "INFY",
        "name": "Infosys Ltd",
        "exchange": "NSE",
        "sector": "Information Technology",
        "industry": "IT Services & Consulting",
        "description": (
            "Infosys, co-founded in 1981 by N. R. Narayana Murthy and six partners, is widely credited "
            "as a pioneer of India's IT services and outsourcing industry. It is now India's "
            "second-largest IT services company, offering consulting, technology, digital "
            "transformation, and cloud and AI services to clients in more than 50 countries, with a "
            "particularly strong presence in the United States and Europe. Infosys also runs one of "
            "India's most respected corporate training campuses, in Mysuru."
        ),
    },
    {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank Ltd",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Private Sector Bank",
        "description": (
            "HDFC Bank is India's largest private-sector bank by assets and market capitalisation, "
            "offering retail and corporate banking, wealth management, and payments across an "
            "extensive branch and ATM network. In 2023 it completed a merger with its parent, "
            "mortgage lender HDFC Ltd, in one of the largest corporate mergers in Indian history, "
            "combining a leading deposit franchise with a leading home-loan book. The bank has also "
            "invested heavily in digital banking and remains one of the most closely tracked stocks "
            "on Indian exchanges."
        ),
    },
    {
        "symbol": "ICICIBANK",
        "name": "ICICI Bank Ltd",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Private Sector Bank",
        "description": (
            "ICICI Bank is one of India's largest private-sector banks, with a strong retail lending "
            "franchise spanning home loans, auto loans, and credit cards alongside corporate and "
            "international banking. Its group companies include major players in life and general "
            "insurance and asset management, and the bank has pushed hard into digital banking through "
            "its iMobile Pay app. ICICI Bank consistently ranks among the top private banks in India by "
            "market capitalisation."
        ),
    },
    {
        "symbol": "SBIN",
        "name": "State Bank of India",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Public Sector Bank",
        "description": (
            "State Bank of India is the country's largest bank by assets and branch network, with a "
            "history tracing back over two centuries to the Bank of Calcutta. Majority-owned by the "
            "Government of India, SBI is systemically important to the Indian banking system and plays "
            "a central role in government banking, pensions, and payments infrastructure, alongside a "
            "full range of retail, corporate, and international banking services. It also has a "
            "significant international footprint through overseas branches and subsidiaries."
        ),
    },
    {
        # In October 2025, Tata Motors demerged into two separately-listed
        # companies - TMCV kept the original entity/trading history, TMPV is
        # newly listed. See app/services/market_data_sync.py and the
        # migration note in memory for how existing rows were split.
        "symbol": "TMCV",
        "name": "Tata Motors Limited",
        "exchange": "NSE",
        "sector": "Automobile",
        "industry": "Commercial Vehicles",
        "description": (
            "Tata Motors Limited is the commercial-vehicles business that continued under the original "
            "Tata Motors entity after its October 2025 demerger split it from the passenger-vehicles "
            "business (now Tata Motors Passenger Vehicles Ltd). Part of the Tata Group, it is one of "
            "India's largest manufacturers of trucks, buses, and other commercial vehicles, with a "
            "significant share of the domestic commercial vehicle market and exports to several "
            "countries."
        ),
    },
    {
        "symbol": "TMPV",
        "name": "Tata Motors Passenger Vehicles Ltd",
        "exchange": "NSE",
        "sector": "Automobile",
        "industry": "Passenger Vehicles",
        "description": (
            "Tata Motors Passenger Vehicles Ltd was listed separately in October 2025 when Tata Motors "
            "demerged into commercial-vehicle (TMCV) and passenger-vehicle (TMPV) entities. It makes "
            "the Tiago, Punch, Nexon, and Harrier, among others, and has been a leading force in India's "
            "electric passenger vehicle market through its Tata.ev lineup."
        ),
    },
    {
        "symbol": "BHARTIARTL",
        "name": "Bharti Airtel Ltd",
        "exchange": "NSE",
        "sector": "Telecommunications",
        "industry": "Telecom Services",
        "description": (
            "Bharti Airtel is one of India's largest telecommunications operators, providing mobile, "
            "broadband, DTH, and enterprise digital services. Alongside Reliance Jio, it has been a "
            "central player in India's telecom consolidation and the shift to widespread affordable "
            "mobile data, and it also operates a substantial telecom business across several African "
            "markets through Airtel Africa."
        ),
    },
    {
        "symbol": "ITC",
        "name": "ITC Ltd",
        "exchange": "NSE",
        "sector": "Fast-Moving Consumer Goods",
        "industry": "Diversified FMCG",
        "description": (
            "ITC is one of India's most diversified conglomerates, with roots in cigarettes and "
            "tobacco - still a major profit contributor - alongside a large fast-moving consumer goods "
            "business built around brands like Aashirvaad, Sunfeast, Bingo, and Classmate. It also "
            "operates a chain of ITC Hotels, one of India's largest paperboard and packaging "
            "businesses, an agribusiness trading arm, and an information technology subsidiary, ITC "
            "Infotech."
        ),
    },
    {
        "symbol": "LT",
        "name": "Larsen & Toubro Ltd",
        "exchange": "NSE",
        "sector": "Construction",
        "industry": "Engineering & Construction",
        "description": (
            "Larsen & Toubro is one of India's largest engineering, procurement, and construction "
            "conglomerates, executing large-scale infrastructure, power, and defence projects across "
            "India and the Middle East. Its businesses extend into heavy engineering and manufacturing, "
            "and it holds a significant stake in IT services through LTIMindtree, making it one of the "
            "most diversified industrial groups on Indian exchanges."
        ),
    },
    {
        "symbol": "MARUTI",
        "name": "Maruti Suzuki India Ltd",
        "exchange": "NSE",
        "sector": "Automobile",
        "industry": "Passenger Vehicles",
        "description": (
            "Maruti Suzuki India is the country's largest passenger vehicle manufacturer by sales "
            "volume and market share, a joint venture with Japan's Suzuki Motor Corporation. Its "
            "lineup spans entry-level hatchbacks to SUVs, sold through one of the largest dealership "
            "and service networks in the country, and it has long been the default choice for many "
            "first-time car buyers in India."
        ),
    },
    {
        "symbol": "SUNPHARMA",
        "name": "Sun Pharmaceutical Industries Ltd",
        "exchange": "NSE",
        "sector": "Healthcare",
        "industry": "Pharmaceuticals",
        "description": (
            "Sun Pharmaceutical Industries is India's largest pharmaceutical company by revenue and "
            "market capitalisation, founded by Dilip Shanghvi. It has a major global generics business, "
            "with a particularly large presence in the United States, alongside a growing specialty "
            "pharmaceuticals portfolio in dermatology, ophthalmology, and oncology."
        ),
    },
    {
        "symbol": "HINDUNILVR",
        "name": "Hindustan Unilever Ltd",
        "exchange": "NSE",
        "sector": "Fast-Moving Consumer Goods",
        "industry": "Personal & Household Care",
        "description": (
            "Hindustan Unilever is India's largest fast-moving consumer goods company, majority-owned "
            "by global consumer giant Unilever. Its portfolio includes some of the most recognised "
            "household names in the country - Lux, Dove, Surf Excel, Lifebuoy, Horlicks, and Brooke "
            "Bond among them - spanning home care, personal care, and food, distributed through an "
            "exceptionally deep rural and urban retail network."
        ),
    },
    {
        "symbol": "ASIANPAINT",
        "name": "Asian Paints Ltd",
        "exchange": "NSE",
        "sector": "Consumer Durables",
        "industry": "Paints",
        "description": (
            "Asian Paints is India's largest paint and coatings company, with a long-standing lead in "
            "the decorative paints market and a growing presence in industrial coatings, waterproofing, "
            "and home decor. It operates across Asia, the Middle East, and Africa, and its brand is "
            "closely associated with home painting and renovation in India."
        ),
    },
    {
        "symbol": "BAJFINANCE",
        "name": "Bajaj Finance Ltd",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Non-Banking Financial Company",
        "description": (
            "Bajaj Finance is one of India's leading non-banking financial companies (NBFCs), part of "
            "the Bajaj Group. It offers a broad range of lending products - from consumer durable and "
            "personal loans to SME and commercial finance - alongside deposits and wealth management, "
            "built on a widely used digital lending platform and one of the fastest-growing loan books "
            "among Indian NBFCs."
        ),
    },
]
