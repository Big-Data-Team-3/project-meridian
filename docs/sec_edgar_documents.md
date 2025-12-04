# SEC EDGAR Document Types for Extraction

Based on the Meridian project proposal, the platform extracts and processes specific SEC EDGAR filing types to enable fundamental analysis of publicly traded companies.

## Primary Document Types for Extraction

### 1. **10-K (Annual Report)**
- **Form Type**: 10-K
- **Filing Frequency**: Annual (fiscal year-end)
- **Purpose**: Comprehensive annual report providing complete overview of company's financial condition
- **Key Content**:
  - Business description and operations
  - Risk factors
  - Financial statements (Balance Sheet, Income Statement, Cash Flow)
  - Management's Discussion & Analysis (MD&A)
  - Executive compensation
  - Legal proceedings
- **Analysis Value**: Fundamental analysis, company health assessment, long-term trends
- **Typical Size**: 50-200 pages
- **Volume Impact**: Largest contributor to daily SEC EDGAR volume (~200MB/day total)

### 2. **10-Q (Quarterly Report)**
- **Form Type**: 10-Q
- **Filing Frequency**: Quarterly (within 40-45 days of quarter-end)
- **Purpose**: Update on company's financial condition and operations
- **Key Content**:
  - Unaudited financial statements
  - Management's Discussion & Analysis (MD&A)
  - Market risk disclosures
  - Controls and procedures
  - Legal proceedings updates
- **Analysis Value**: Short-term performance tracking, quarterly trends, earnings analysis
- **Typical Size**: 20-80 pages
- **Volume Impact**: Significant contributor to daily filing volume

### 3. **8-K (Current Report)**
- **Form Type**: 8-K
- **Filing Frequency**: As needed (material events)
- **Purpose**: Report material corporate events that shareholders should know about
- **Key Content**:
  - Entry into material agreements
  - Results of operations and financial condition
  - Changes in control of registrant
  - Departure of directors/officers
  - Amendments to charter/bylaws
  - Material impairments
  - Changes in accountants
  - Other events (bankruptcy, delisting, etc.)
- **Analysis Value**: Real-time event monitoring, risk assessment, market-moving news
- **Typical Size**: 5-50 pages
- **Volume Impact**: Variable, event-driven filings

## Extraction Strategy

### **Document Processing Pipeline**
1. **Raw Download**: HTML, XML, or text formats from SEC EDGAR APIs
2. **Text Extraction**: Convert structured filings to clean text for analysis
3. **Metadata Capture**: Filing date, company CIK, form type, period end date
4. **Content Parsing**: Extract structured data (financial tables, MD&A sections)
5. **Embedding Generation**: Create vector representations for semantic search
6. **Storage**: Raw files in GCS, processed text in PostgreSQL, embeddings in Chroma

### **Libraries for Extraction**
- `sec-edgar-api==1.1.0`: API client for SEC EDGAR data
- `secedgar==0.6.0`: SEC EDGAR filings downloader
- `sec-edgar-downloader==5.0.3`: Additional SEC EDGAR utilities

### **Data Volume Estimates**
- **10-K**: ~50-60% of total SEC EDGAR volume (largest files)
- **10-Q**: ~30-40% of volume (regular quarterly updates)
- **8-K**: ~10-20% of volume (variable frequency, smaller files)
- **Total SEC EDGAR**: ~200MB/day, ~73GB/year

## Use Cases in Financial Analysis

### **Fundamental Analysis**
- Company valuation and financial health assessment
- Competitive analysis and industry benchmarking
- Risk factor identification and monitoring

### **Event-Driven Analysis**
- Real-time monitoring of material corporate events
- Impact assessment of mergers, acquisitions, or leadership changes
- Regulatory compliance monitoring

### **Research & Reporting**
- Automated summarization of lengthy filings
- Trend analysis across multiple periods
- Comparative analysis between companies

## Technical Considerations

### **File Formats**
- **HTML**: Most common format, requires text extraction
- **XML**: Structured format, easier parsing
- **Plain Text**: Direct text files (less common)

### **Processing Challenges**
- Large document sizes (10-K can exceed 100 pages)
- Complex formatting and tables
- XBRL (eXtensible Business Reporting Language) integration
- Rate limiting and API constraints

### **Storage Strategy**
- **Raw Storage**: GCS for original filings
- **Processed Storage**: PostgreSQL for structured data
- **Vector Storage**: Chroma for semantic search of document content

## Extraction Scope
- **Focus**: Publicly traded companies (NYSE, NASDAQ, etc.)
- **Coverage**: All companies filing these forms
- **Historical Depth**: As needed for analysis (typically 3-5 years)
- **Update Frequency**: Daily batch processing to capture new filings


----

Use native SEC formats (HTML, XML, TXT) from `sec-edgar` rather than PDFs. Here's why:

## **Why Native Formats (HTML/XML/TXT) Are Better**

### **1. LLM Processing & Embeddings**
- **Native formats**: Already text-based, easy to extract clean text for embeddings
- **PDFs**: Require PDF parsing libraries (PyPDF2, pdfplumber), may need OCR for scanned PDFs, harder to extract clean text

### **2. Storage Efficiency**
- **Native formats**: Smaller file sizes (text is compressed)
- **PDFs**: Larger files, especially with images/tables
- **Impact**: With ~200MB/day, PDFs could be 2-3x larger

### **3. Processing Speed**
- **Native formats**: Direct text extraction, faster processing
- **PDFs**: Slower parsing, more CPU-intensive

### **4. Structured Data Extraction**
- **Native formats**: HTML/XML have structure you can parse (tables, sections)
- **PDFs**: Harder to extract structured data reliably

### **5. Your Current Setup**
Looking at your files, you're already getting `.txt` files (native SEC format), which is the right approach.

## **Recommended Format Priority**

1. **XML** (if available): Best for structured parsing
2. **HTML**: Good for structured content, easy to parse
3. **TXT**: Simplest, already text-based, good for LLM processing

## **What `sec-edgar-api` vs `sec-edgar` Provides**

Both libraries can get native formats. Check which gives you:
- Better format options (XML > HTML > TXT)
- Cleaner text extraction
- More reliable API

## **For Your Use Case**

Since you need to:
- Generate embeddings (text-embedding-3-small)
- Summarize documents (GPT models)
- Store efficiently
- Process at scale

**Stick with native formats (HTML/XML/TXT) from `sec-edgar`** - avoid PDFs unless you specifically need the visual formatting for human review.

The native formats align perfectly with your LLM processing pipeline and will save significant storage and processing costs.

---

For Your Pipeline

- Priority order for identification:
- Context (surrounding text) - Most reliable
- XBRL tags - Indicates structured financial data
- Content keywords - Financial terms, form-specific terms
- Structure - Column/row patterns
- Position - Where in document
- Practical tip: Start with context-based identification since SEC forms follow standard structures. Tables near "Item X.XX" are content tables,  tables with "Exhibit No." are exhibits tables, etc.
- This approach will help you categorize tables appropriately for your  text extraction and structured data processing pipeline.