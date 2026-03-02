import { useState } from 'react'

const API = '/api'

export default function SubscribeForm() {
    const [email, setEmail] = useState('')
    const [status, setStatus] = useState(null) // null | 'loading' | 'success' | 'error'
    const [message, setMessage] = useState('')

    async function handleSubmit(e) {
        e.preventDefault()
        if (!email) return

        setStatus('loading')
        setMessage('')

        try {
            const res = await fetch(`${API}/subscribe`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            })

            const data = await res.json()

            if (!res.ok) {
                throw new Error(data.detail || `Error ${res.status}`)
            }

            setStatus('success')
            setMessage(data.message || `Newsletter sent to ${email}!`)
            setEmail('')
        } catch (err) {
            setStatus('error')
            setMessage(err.message)
        }
    }

    return (
        <section className="subscribe-section">
            <h2>Get the newsletter</h2>
            <p>Enter your email to receive today's curated AI news digest.</p>
            <form className="subscribe-form" onSubmit={handleSubmit}>
                <input
                    id="subscribe-email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    disabled={status === 'loading'}
                />
                <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={status === 'loading' || !email}
                >
                    {status === 'loading' ? 'Sending…' : 'Send Newsletter'}
                </button>
            </form>
            {message && (
                <p className={`form-message ${status === 'success' ? 'success' : 'error'}`}>
                    {message}
                </p>
            )}
        </section>
    )
}
