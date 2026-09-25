export type StockEvent = { date: string; kind: 'results' | 'corporate' | 'news'; label: string };
export type StockInfo = {
  name: string; founded: string; hq: string;
  about: string; history: string; events: StockEvent[];
};

// Company facts and events sourced from Wikipedia company articles; results
// dates from company IR pages (tcs.com, infosys.com). Curated 25 September 2026.
// See INFO_FRESHNESS in App.tsx.
export const STOCK_INFO: Record<string, StockInfo> = {
  RELIANCE: {
    name: 'Reliance Industries Ltd', founded: '1958', hq: 'Mumbai',
    about: 'India\'s largest public company by market capitalisation and revenue - a conglomerate spanning energy, petrochemicals, natural gas, retail, telecommunications (Jio) and media.',
    history: 'Founded by Dhirubhai Ambani in 1958 as a textiles trading business, it grew backwards into petrochemicals and refining, then outwards into retail and telecom, where Jio reshaped Indian mobile data from 2016.',
    events: [],
  },
  HDFCBANK: {
    name: 'HDFC Bank Ltd', founded: '1994', hq: 'Mumbai',
    about: 'India\'s largest private sector bank by assets and market capitalisation, offering retail, wholesale and treasury banking.',
    history: 'Incorporated in August 1994 after the RBI opened banking to the private sector, it started operations in January 1995 and grew into one of the ten largest banks in the world by market capitalisation.',
    events: [],
  },
  INFY: {
    name: 'Infosys Ltd', founded: '1981', hq: 'Bengaluru',
    about: 'Multinational technology company in IT services, business consulting and outsourcing - one of the Big Six Indian IT companies.',
    history: 'Founded in 1981 in Pune by seven engineers with a small pool of capital, it moved to Bengaluru and became the first India-registered company listed on a US stock exchange.',
    events: [
      { date: '23 Jul 2026', kind: 'results', label: 'Q1 FY27 results announced (quarter ended 30 June 2026), per the company\'s IR page' },
    ],
  },
  TCS: {
    name: 'Tata Consultancy Services Ltd', founded: '1968', hq: 'Mumbai',
    about: 'IT services and consulting multinational, part of the Tata Group, operating across 46 countries.',
    history: 'Founded in 1968 as a division of Tata Sons, it pioneered the offshore delivery model for software services and became the group\'s largest listed company.',
    events: [
      { date: '9 Jul 2026', kind: 'results', label: 'Q1 FY27 results: revenue US$7,624M, +2.7% YoY, net margin 19.2%, per tcs.com' },
    ],
  },
  ADANIENT: {
    name: 'Adani Enterprises Ltd', founded: '1993', hq: 'Ahmedabad',
    about: 'Holding company of the Adani Group - coal and iron-ore mining and trading, plus airport operations, data centres, roads and solar manufacturing through subsidiaries.',
    history: 'Founded in 1993 by Gautam Adani as a commodities trading house, it became the incubator for the group\'s infrastructure businesses, several of which were later listed separately.',
    events: [],
  },
  SBIN: {
    name: 'State Bank of India', founded: '1955', hq: 'Mumbai',
    about: 'India\'s largest bank - a public sector bank with about 23% market share by assets and over 500 million customers.',
    history: 'Descends from the Bank of Calcutta (1806) through the Imperial Bank of India (1921); nationalised and renamed State Bank of India in 1955.',
    events: [],
  },
  SUZLON: {
    name: 'Suzlon Energy Ltd', founded: '1995', hq: 'Pune',
    about: 'Wind turbine manufacturer - designs, builds and maintains wind farms across India and abroad.',
    history: 'Tulsi Tanti founded it in 1995 after buying wind turbines to power his textile factory and finding energy the better business; the first customer turbine was commissioned in 1996.',
    events: [],
  },
  TATAMOTORS: {
    name: 'Tata Motors Ltd', founded: '1945', hq: 'Mumbai',
    about: 'Commercial vehicle manufacturer in the Tata Group - trucks, vans and buses (the passenger-vehicle business was demerged into a separate listed company).',
    history: 'Founded in 1945 as a locomotive maker, it moved into trucks in the 1950s and grew into India\'s largest commercial vehicle maker.',
    events: [],
  },
  IRFC: {
    name: 'Indian Railway Finance Corporation Ltd', founded: '1986', hq: 'New Delhi',
    about: 'Public sector undertaking that raises funds from capital markets and borrowings to finance Indian Railways\' expansion and operations.',
    history: 'Set up in December 1986 as the railways\' dedicated financing arm, listed in 2021, and granted Navaratna status in March 2025.',
    events: [
      { date: 'Mar 2025', kind: 'news', label: 'Granted Navaratna status by the Government of India - the 26th PSU on the list' },
    ],
  },
  YESBANK: {
    name: 'Yes Bank Ltd', founded: '2004', hq: 'Mumbai',
    about: 'Private sector bank serving retail, MSME and corporate clients, with about 1,300 branches across 300 districts.',
    history: 'Founded in 2004 by Rana Kapoor and Ashok Kapur, it grew fast before a 2020 reconstruction led by a consortium of banks, and has since rebuilt its balance sheet.',
    events: [],
  },
  PAYTM: {
    name: 'One97 Communications Ltd (Paytm)', founded: '2000', hq: 'Noida',
    about: 'Fintech company behind Paytm - digital payments and financial services for consumers and merchants.',
    history: 'Founded in 2000 by Vijay Shekhar Sharma, it launched Paytm in 2009 and listed in November 2021 in what was then India\'s largest IPO.',
    events: [
      { date: '8 Nov 2021', kind: 'corporate', label: 'Listed on Indian exchanges after what was then India\'s largest IPO' },
    ],
  },
  ZOMATO: {
    name: 'Zomato (Eternal Ltd)', founded: '2008', hq: 'Gurugram',
    about: 'Online food ordering and delivery service operating in 800+ Indian cities, owned by Eternal Limited.',
    history: 'Started in 2008 as FoodieBay, a restaurant-listing site built by Deepinder Goyal and Pankaj Chaddah, renamed Zomato in 2010, and made food delivery its core business from 2015.',
    events: [
      { date: 'Aug 2024', kind: 'corporate', label: 'Acquired Paytm\'s entertainment and ticketing businesses; District app launched Nov 2024' },
    ],
  },
};
