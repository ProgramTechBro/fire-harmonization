export default function PageHeader({ kicker, title, children, aside }) {
  return (
    <header className="page-band">
      <div className="page-band-inner">
        <div className="page-band-text">
          {kicker && <p className="kicker">{kicker}</p>}
          <h1>{title}</h1>
          {children && <p className="page-intro">{children}</p>}
        </div>
        {aside && <div className="page-band-aside">{aside}</div>}
      </div>
    </header>
  );
}
