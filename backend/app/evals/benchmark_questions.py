from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BenchmarkQuestion:
    id: int
    title: str
    query: str
    primary_tickers: list[str]
    expected_topics: list[str]
    is_refusal_test: bool = False


BENCHMARK_QUESTIONS: list[BenchmarkQuestion] = [
    BenchmarkQuestion(
        id=1,
        title="Apple Revenue Mix Shift",
        query="Across Apple's 10-K filings, how did the revenue mix between iPhone, Services, Mac, iPad, and Wearables change, and which category appears to have contributed most to any mix shift?",
        primary_tickers=["AAPL"],
        expected_topics=["iPhone", "Services", "Mac", "net sales", "revenue"],
    ),
    BenchmarkQuestion(
        id=2,
        title="Amazon AWS vs Regional Segments",
        query="For Amazon, compare AWS operating income and margin against North America and International. In which years did AWS appear to fund losses or weaker profitability elsewhere?",
        primary_tickers=["AMZN"],
        expected_topics=["AWS", "North America", "International", "operating income"],
    ),
    BenchmarkQuestion(
        id=3,
        title="NVIDIA Data Center Drivers & Constraints",
        query="How did NVIDIA describe demand drivers, customer concentration, and supply constraints for its Data Center business?",
        primary_tickers=["NVDA"],
        expected_topics=["Data Center", "customer", "supply", "Compute & Networking"],
    ),
    BenchmarkQuestion(
        id=4,
        title="Microsoft Azure & Cloud Capacity",
        query="Across Microsoft's filings, what changed in the way the company describes Azure, AI infrastructure, and cloud capacity constraints?",
        primary_tickers=["MSFT"],
        expected_topics=["Azure", "Intelligent Cloud", "capacity", "infrastructure"],
    ),
    BenchmarkQuestion(
        id=5,
        title="Alphabet Revenue Segments",
        query="For Alphabet, how did Google Search, YouTube ads, Google Network, subscriptions/platforms/devices, and Google Cloud revenue trends differ?",
        primary_tickers=["GOOGL"],
        expected_topics=["Google Search", "YouTube", "Google Cloud", "advertising"],
    ),
    BenchmarkQuestion(
        id=6,
        title="Cross-Company Risk Factor Changes",
        query="Which companies discuss risk-factor language related to AI, cloud infrastructure, export controls, supply chain concentration, or regulation?",
        primary_tickers=["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"],
        expected_topics=["Risk Factors", "Item 1A", "export controls", "regulation"],
    ),
    BenchmarkQuestion(
        id=7,
        title="Supplier Concentration: Apple & NVIDIA",
        query="For Apple and NVIDIA, what do the filings say about supplier concentration or dependence on third-party manufacturing?",
        primary_tickers=["AAPL", "NVDA"],
        expected_topics=["supplier", "manufacturing", "third-party", "concentration"],
    ),
    BenchmarkQuestion(
        id=8,
        title="Capex & AI Infrastructure Commitments",
        query="Compare capital expenditures and purchase commitments for Microsoft, Alphabet, Amazon, and NVIDIA related to cloud and AI infrastructure.",
        primary_tickers=["MSFT", "GOOGL", "AMZN", "NVDA"],
        expected_topics=["capital expenditures", "property and equipment", "commitments"],
    ),
    BenchmarkQuestion(
        id=9,
        title="Geographic Revenue Exposures",
        query="Summarize the most important geographic revenue exposures disclosed in the latest 10-K filings across the companies.",
        primary_tickers=["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"],
        expected_topics=["geographic", "United States", "China", "International"],
    ),
    BenchmarkQuestion(
        id=10,
        title="Generative AI Margins (Refusal & Grounding Boundary)",
        query="Do the SEC filings prove that generative AI improved profit margins for any of these companies, or must we refuse to infer beyond direct disclosures?",
        primary_tickers=["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"],
        expected_topics=["generative AI", "margin", "refuse", "evidence"],
        is_refusal_test=True,
    ),
]
