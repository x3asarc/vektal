// Minimal placeholder page
// Full frontend development in Phase 7

export default function Home() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      fontFamily: 'system-ui, sans-serif',
      backgroundColor: '#f5f5f5'
    }}>
      <h1 style={{ marginBottom: '1rem' }}>
        Shopify Multi-Supplier Platform
      </h1>
      <p style={{ color: '#666', marginBottom: '2rem' }}>
        Frontend placeholder - Full UI coming in Phase 7
      </p>
      <div style={{
        padding: '1rem 2rem',
        backgroundColor: '#fff',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <h3>Docker Stack Status</h3>
        <ul style={{ textAlign: 'left', lineHeight: '1.8' }}>
          <li>Frontend (Next.js): Running on port 3000</li>
          <li>Backend API: <a href="/api/health">/api/health</a></li>
          <li>Primary access: <a href="http://localhost">http://localhost</a> (via Nginx)</li>
        </ul>
      </div>
      <p style={{ marginTop: '2rem', fontSize: '0.875rem', color: '#999' }}>
        Access Flask directly: <a href="http://localhost:5000/health">localhost:5000/health</a>
      </p>
    </div>
  );
}
