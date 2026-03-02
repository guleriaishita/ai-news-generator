import { useState, useEffect, useCallback } from 'react'
import ArticleCard from './components/ArticleCard.jsx'
import SubscribeForm from './components/SubscribeForm.jsx'
import NewsletterModal from './components/NewsletterModal.jsx'

const API = '/api'


export default function App() {
    const [articles, setArticles] = useState([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [showPreview, setShowPreview] = useState(false)
    const [hasFetched, setHasFetched] = useState(false)

    const fetchNews = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch(`${API}/news`)
            if (!res.ok) throw new Error(`Server error: ${res.status}`)
            const data = await res.json()
            setArticles(data.articles || [])
            setHasFetched(true)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchNews()
    }, [fetchNews])

    const filtered = articles

    return (
        <>
            <header>
                <div className="container">
                    <div className="site-title">
                        <span className="dot" />
                        AI News Aggregator
                    </div>
                    <button
                        className="btn btn-outline"
                        onClick={() => setShowPreview(true)}
                        disabled={articles.length === 0}
                    >
                        Newsletter Preview
                    </button>
                </div>
            </header>

            <main>
                <div className="container">
                    {/* Subscribe */}
                    <SubscribeForm />

                    <div className="news-controls">
                        <button
                            className="btn btn-outline refresh-btn"
                            onClick={fetchNews}
                            disabled={loading}
                        >
                            {loading ? 'Refreshing…' : 'Refresh News'}
                        </button>
                    </div>

                    {hasFetched && !loading && !error && (
                        <div className="section-header">
                            <span className="section-title">Latest AI News</span>
                            <span className="count-badge">
                                {articles.length} article{articles.length !== 1 ? 's' : ''} found
                            </span>
                        </div>
                    )}

                    {/* States */}
                    {loading && (
                        <div className="state-box">
                            <div className="spinner" />
                            Fetching and analysing news via AI…
                        </div>
                    )}

                    {!loading && error && (
                        <div className="state-box">
                            ⚠️ {error}
                            <br /><br />
                            <button className="btn btn-primary" onClick={fetchNews}>Retry</button>
                        </div>
                    )}

                    {!loading && !error && hasFetched && filtered.length === 0 && (
                        <div className="state-box">
                            No articles found{activeCategory !== 'All' ? ` in "${activeCategory}"` : ''}.
                        </div>
                    )}

                    {/* Grid */}
                    {!loading && !error && filtered.length > 0 && (
                        <div className="articles-grid">
                            {filtered.map((article, idx) => (
                                <ArticleCard key={article.url || idx} article={article} />
                            ))}
                        </div>
                    )}
                </div>
            </main>

            <footer>
                <p>AI News Aggregator · Powered by NewsAPI + OpenRouter · {new Date().getFullYear()}</p>
            </footer>

            {showPreview && (
                <NewsletterModal onClose={() => setShowPreview(false)} />
            )}
        </>
    )
}
