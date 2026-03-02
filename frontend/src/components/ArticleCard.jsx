const CATEGORY_CLASSES = {
    'AI Tools': 'cat-ai-tools',
    'Industry News': 'cat-industry',
    'Ethics': 'cat-ethics',
    'Research': 'cat-research',
}

function formatDate(iso) {
    if (!iso) return ''
    try {
        return new Date(iso).toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
        })
    } catch {
        return ''
    }
}

export default function ArticleCard({ article }) {
    const {
        title, summary, category, url, source,
        publishedAt, urlToImage,
    } = article

    const catClass = CATEGORY_CLASSES[category] || 'cat-default'
    const date = formatDate(publishedAt)

    return (
        <article className="article-card">
            {urlToImage && (
                <img
                    className="article-thumb"
                    src={urlToImage}
                    alt=""
                    loading="lazy"
                    onError={e => { e.target.style.display = 'none' }}
                />
            )}
            <div className="article-body">
                <div className="article-meta">
                    <span className={`category-tag ${catClass}`}>{category}</span>
                    {source && (
                        <span className="article-source">
                            {url ? (
                                <a href={url} target="_blank" rel="noopener noreferrer">{source}</a>
                            ) : (
                                source
                            )}
                        </span>
                    )}
                    {date && <span className="article-date">{date}</span>}
                </div>
                <h2 className="article-title">
                    {url ? (
                        <a href={url} target="_blank" rel="noopener noreferrer">{title}</a>
                    ) : (
                        title
                    )}
                </h2>
                {summary && (
                    <p className="article-summary">{summary}</p>
                )}
                {url && (
                    <div className="article-footer">
                        <a href={url} target="_blank" rel="noopener noreferrer" className="read-more">
                            Read full article →
                        </a>
                    </div>
                )}
            </div>
        </article>
    )
}
