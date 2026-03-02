import { useState, useEffect, useRef } from 'react'

const API = '/api'

export default function NewsletterModal({ onClose }) {
    const [html, setHtml] = useState('')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const iframeRef = useRef(null)

    useEffect(() => {
        let cancelled = false

        async function load() {
            try {
                const res = await fetch(`${API}/newsletter/preview`)
                if (!res.ok) throw new Error(`Server error: ${res.status}`)
                const text = await res.text()
                if (!cancelled) setHtml(text)
            } catch (err) {
                if (!cancelled) setError(err.message)
            } finally {
                if (!cancelled) setLoading(false)
            }
        }

        load()
        return () => { cancelled = true }
    }, [])

    // Write HTML into the iframe after it's loaded
    useEffect(() => {
        if (html && iframeRef.current) {
            const doc = iframeRef.current.contentDocument
            if (doc) {
                doc.open()
                doc.write(html)
                doc.close()
            }
        }
    }, [html])

    // Close on Escape
    useEffect(() => {
        function onKey(e) { if (e.key === 'Escape') onClose() }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [onClose])

    return (
        <div
            className="modal-overlay"
            onClick={e => { if (e.target === e.currentTarget) onClose() }}
            role="dialog"
            aria-modal="true"
            aria-label="Newsletter preview"
        >
            <div className="modal">
                <div className="modal-header">
                    <h3>Newsletter Preview</h3>
                    <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
                </div>
                <div className="modal-body">
                    {loading && (
                        <div className="state-box">
                            <div className="spinner" />
                            Loading preview…
                        </div>
                    )}
                    {!loading && error && (
                        <div className="state-box">⚠️ {error}</div>
                    )}
                    {!loading && !error && (
                        <iframe
                            ref={iframeRef}
                            title="Newsletter Preview"
                            sandbox="allow-same-origin"
                        />
                    )}
                </div>
            </div>
        </div>
    )
}
