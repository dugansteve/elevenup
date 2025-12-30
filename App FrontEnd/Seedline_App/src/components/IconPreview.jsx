// Preview component to showcase all flat icons
// Temporary file - can be deleted after review

import {
  TeamsIcon,
  ClubsIcon,
  PlayersIcon,
  BadgesIcon,
  SimulationIcon,
  TournamentIcon,
  SettingsIcon,
  LogoutIcon
} from './PaperIcons';

function IconPreview() {
  const icons = [
    { name: 'Teams', component: TeamsIcon, description: 'Trophy with handles' },
    { name: 'Clubs', component: ClubsIcon, description: 'Shield with soccer pentagon' },
    { name: 'Players', component: PlayersIcon, description: 'Two person silhouettes' },
    { name: 'Badges', component: BadgesIcon, description: 'Medal with star and ribbon' },
    { name: 'Simulation', component: SimulationIcon, description: 'Bar chart with trend line' },
    { name: 'Tournament', component: TournamentIcon, description: 'Map pin location marker' },
    { name: 'Settings', component: SettingsIcon, description: 'Gear cog' },
    { name: 'Logout', component: LogoutIcon, description: 'Door with exit arrow' },
  ];

  return (
    <div style={{
      padding: '2rem',
      background: '#f5f5f5',
      minHeight: '100vh',
      fontFamily: 'system-ui, sans-serif'
    }}>
      <h1 style={{ marginBottom: '0.5rem', color: '#2D5016' }}>
        Flat Icon Set
      </h1>
      <p style={{ color: '#666', marginBottom: '2rem' }}>
        Clean, minimal flat icons for Seedline menu
      </p>

      {/* Size comparison */}
      <div style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '1rem', color: '#444', marginBottom: '1rem' }}>
          Size Comparison
        </h2>
        <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          {[16, 24, 32, 48, 64].map(size => (
            <div key={size} style={{ textAlign: 'center' }}>
              <div style={{
                background: 'white',
                padding: '1rem',
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                marginBottom: '0.5rem'
              }}>
                <TeamsIcon size={size} color="green" />
              </div>
              <span style={{ fontSize: '0.75rem', color: '#888' }}>{size}px</span>
            </div>
          ))}
        </div>
      </div>

      {/* All icons grid */}
      <h2 style={{ fontSize: '1rem', color: '#444', marginBottom: '1rem' }}>
        Full Icon Set (Green Theme)
      </h2>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
        gap: '1rem',
        marginBottom: '3rem'
      }}>
        {icons.map(({ name, component: Icon, description }) => (
          <div key={name} style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '12px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.75rem'
          }}>
            <Icon size={48} color="green" />
            <div style={{ fontWeight: '600', color: '#2D5016' }}>{name}</div>
            <div style={{ fontSize: '0.75rem', color: '#888', textAlign: 'center' }}>
              {description}
            </div>
          </div>
        ))}
      </div>

      {/* Gray variant */}
      <h2 style={{ fontSize: '1rem', color: '#444', marginBottom: '1rem' }}>
        Gray Variant
      </h2>
      <div style={{
        display: 'flex',
        gap: '1rem',
        flexWrap: 'wrap',
        marginBottom: '3rem'
      }}>
        {icons.map(({ name, component: Icon }) => (
          <div key={name} style={{
            background: 'white',
            padding: '1rem',
            borderRadius: '8px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <Icon size={32} color="gray" />
            <span style={{ fontSize: '0.7rem', color: '#888' }}>{name}</span>
          </div>
        ))}
      </div>

      {/* On dark background */}
      <h2 style={{ fontSize: '1rem', color: '#444', marginBottom: '1rem' }}>
        On Dark Background
      </h2>
      <div style={{
        background: 'linear-gradient(135deg, #2D5016 0%, #4A7C2A 100%)',
        padding: '2rem',
        borderRadius: '12px',
        display: 'flex',
        gap: '2rem',
        flexWrap: 'wrap',
        justifyContent: 'center'
      }}>
        {icons.map(({ name, component: Icon }) => (
          <div key={name} style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <div style={{
              background: 'rgba(255,255,255,0.95)',
              padding: '0.75rem',
              borderRadius: '8px'
            }}>
              <Icon size={32} color="green" />
            </div>
            <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.9)' }}>{name}</span>
          </div>
        ))}
      </div>

      {/* Menu simulation */}
      <h2 style={{ fontSize: '1rem', color: '#444', marginBottom: '1rem', marginTop: '2rem' }}>
        Menu Simulation
      </h2>
      <div style={{
        width: '280px',
        background: 'white',
        borderRadius: '12px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
        overflow: 'hidden'
      }}>
        <div style={{
          background: 'linear-gradient(135deg, #2D5016 0%, #4A7C2A 100%)',
          padding: '1.5rem',
          color: 'white'
        }}>
          <div style={{ fontWeight: '600' }}>Steve Dugan</div>
          <div style={{ fontSize: '0.85rem', opacity: 0.85 }}>Admin</div>
        </div>
        <div style={{ padding: '0.5rem 0' }}>
          {icons.slice(0, 7).map(({ name, component: Icon }, i) => (
            <div key={name} style={{
              display: 'flex',
              alignItems: 'center',
              padding: '0.875rem 1.5rem',
              gap: '1rem',
              background: i === 0 ? 'rgba(45, 80, 22, 0.1)' : 'transparent',
              borderLeft: i === 0 ? '4px solid #2D5016' : '4px solid transparent',
              cursor: 'pointer'
            }}>
              <Icon size={24} color="green" />
              <span style={{
                color: i === 0 ? '#2D5016' : '#333',
                fontWeight: i === 0 ? '600' : '500'
              }}>{name}</span>
            </div>
          ))}
        </div>
        <div style={{ borderTop: '1px solid #e0e0e0', padding: '1rem' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            padding: '0.875rem 1rem',
            gap: '0.75rem',
            background: '#f5f5f5',
            borderRadius: '8px',
            cursor: 'pointer'
          }}>
            <LogoutIcon size={24} color="green" />
            <span style={{ color: '#666' }}>Logout</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default IconPreview;
