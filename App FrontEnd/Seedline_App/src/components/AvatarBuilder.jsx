import { useState, useEffect } from 'react';

/**
 * Customizable avatar builder with face, hair, skin tone, and accessories
 */

// Avatar options
const AVATAR_OPTIONS = {
  skinTone: [
    { id: 'light1', color: '#FFDFC4', name: 'Light' },
    { id: 'light2', color: '#F0C8A0', name: 'Light Tan' },
    { id: 'medium1', color: '#D4A574', name: 'Medium' },
    { id: 'medium2', color: '#C68642', name: 'Tan' },
    { id: 'dark1', color: '#8D5524', name: 'Brown' },
    { id: 'dark2', color: '#5C3A21', name: 'Dark' },
  ],
  faceShape: [
    { id: 'round', name: 'Round', path: 'M50,15 C75,15 85,35 85,55 C85,80 70,90 50,90 C30,90 15,80 15,55 C15,35 25,15 50,15' },
    { id: 'oval', name: 'Oval', path: 'M50,10 C70,10 80,30 80,50 C80,75 68,95 50,95 C32,95 20,75 20,50 C20,30 30,10 50,10' },
    { id: 'square', name: 'Square', path: 'M25,20 L75,20 C80,20 85,25 85,30 L85,75 C85,85 75,90 65,90 L35,90 C25,90 15,85 15,75 L15,30 C15,25 20,20 25,20' },
    { id: 'heart', name: 'Heart', path: 'M50,12 C70,12 85,28 85,45 C85,70 65,92 50,92 C35,92 15,70 15,45 C15,28 30,12 50,12' },
  ],
  hairStyle: [
    { id: 'none', name: 'None', path: '' },
    { id: 'short', name: 'Short', path: 'M25,30 C25,15 35,8 50,8 C65,8 75,15 75,30 L75,35 C75,25 65,18 50,18 C35,18 25,25 25,35 Z' },
    { id: 'medium', name: 'Medium', path: 'M20,35 C20,15 30,5 50,5 C70,5 80,15 80,35 L80,50 C80,35 70,25 50,25 C30,25 20,35 20,50 Z M15,50 L15,60 C15,50 25,45 25,45 M85,50 L85,60 C85,50 75,45 75,45' },
    { id: 'long', name: 'Long', path: 'M15,35 C15,12 28,2 50,2 C72,2 85,12 85,35 L85,75 C85,65 75,55 75,45 C75,30 65,20 50,20 C35,20 25,30 25,45 C25,55 15,65 15,75 Z' },
    { id: 'ponytail', name: 'Ponytail', path: 'M25,30 C25,15 35,8 50,8 C65,8 75,15 75,30 L75,35 C75,25 65,18 50,18 C35,18 25,25 25,35 Z M75,20 L90,25 C95,40 90,55 85,45 C80,35 80,25 75,20' },
    { id: 'bun', name: 'Bun', path: 'M25,30 C25,15 35,8 50,8 C65,8 75,15 75,30 L75,35 C75,25 65,18 50,18 C35,18 25,25 25,35 Z M40,5 A15,15 0 1,1 60,5 A15,15 0 1,1 40,5' },
    { id: 'braids', name: 'Braids', path: 'M20,30 C20,15 32,5 50,5 C68,5 80,15 80,30 L80,40 L85,70 L75,70 L72,40 M20,40 L15,70 L25,70 L28,40' },
  ],
  hairColor: [
    { id: 'black', color: '#090806', name: 'Black' },
    { id: 'brown1', color: '#2C1810', name: 'Dark Brown' },
    { id: 'brown2', color: '#6B4423', name: 'Brown' },
    { id: 'brown3', color: '#B7834A', name: 'Light Brown' },
    { id: 'blonde', color: '#E5C100', name: 'Blonde' },
    { id: 'red', color: '#A55B2A', name: 'Red' },
    { id: 'gray', color: '#888888', name: 'Gray' },
  ],
  accessories: [
    { id: 'none', name: 'None' },
    { id: 'headband', name: 'Headband' },
    { id: 'glasses', name: 'Glasses' },
    { id: 'cap', name: 'Cap' },
  ],
};

// Default avatar config
const DEFAULT_CONFIG = {
  skinTone: 'medium1',
  faceShape: 'oval',
  hairStyle: 'medium',
  hairColor: 'brown2',
  accessory: 'none',
};

export default function AvatarBuilder({ initialConfig, onConfigChange }) {
  const [config, setConfig] = useState(() => ({
    ...DEFAULT_CONFIG,
    ...(initialConfig ? JSON.parse(initialConfig) : {})
  }));

  const [activeTab, setActiveTab] = useState('skinTone');

  // Notify parent of changes
  useEffect(() => {
    if (onConfigChange) {
      onConfigChange(JSON.stringify(config));
    }
  }, [config, onConfigChange]);

  const updateConfig = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  // Get current options
  const currentSkin = AVATAR_OPTIONS.skinTone.find(s => s.id === config.skinTone) || AVATAR_OPTIONS.skinTone[2];
  const currentFace = AVATAR_OPTIONS.faceShape.find(f => f.id === config.faceShape) || AVATAR_OPTIONS.faceShape[1];
  const currentHair = AVATAR_OPTIONS.hairStyle.find(h => h.id === config.hairStyle) || AVATAR_OPTIONS.hairStyle[2];
  const currentHairColor = AVATAR_OPTIONS.hairColor.find(c => c.id === config.hairColor) || AVATAR_OPTIONS.hairColor[2];

  return (
    <div style={styles.container}>
      {/* Avatar Preview */}
      <div style={styles.preview}>
        <svg viewBox="0 0 100 100" style={styles.avatarSvg}>
          {/* Face */}
          <path
            d={currentFace.path}
            fill={currentSkin.color}
            stroke="#ddd"
            strokeWidth="1"
          />

          {/* Eyes */}
          <ellipse cx="35" cy="45" rx="5" ry="6" fill="white" />
          <ellipse cx="65" cy="45" rx="5" ry="6" fill="white" />
          <ellipse cx="35" cy="46" rx="3" ry="4" fill="#4a3728" />
          <ellipse cx="65" cy="46" rx="3" ry="4" fill="#4a3728" />
          <ellipse cx="35" cy="45" rx="1.5" ry="2" fill="black" />
          <ellipse cx="65" cy="45" rx="1.5" ry="2" fill="black" />

          {/* Eyebrows */}
          <path d="M28,38 Q35,35 42,38" fill="none" stroke={currentHairColor.color} strokeWidth="2" strokeLinecap="round" />
          <path d="M58,38 Q65,35 72,38" fill="none" stroke={currentHairColor.color} strokeWidth="2" strokeLinecap="round" />

          {/* Nose */}
          <path d="M50,48 L50,58 L45,62" fill="none" stroke="#c9a080" strokeWidth="1.5" strokeLinecap="round" />

          {/* Mouth */}
          <path d="M40,72 Q50,78 60,72" fill="none" stroke="#c97878" strokeWidth="2" strokeLinecap="round" />

          {/* Hair */}
          {currentHair.path && (
            <path
              d={currentHair.path}
              fill={currentHairColor.color}
              stroke={currentHairColor.color}
              strokeWidth="1"
            />
          )}

          {/* Accessories */}
          {config.accessory === 'headband' && (
            <path
              d="M15,28 Q50,22 85,28"
              fill="none"
              stroke="#e53935"
              strokeWidth="4"
              strokeLinecap="round"
            />
          )}
          {config.accessory === 'glasses' && (
            <>
              <circle cx="35" cy="45" r="10" fill="none" stroke="#333" strokeWidth="2" />
              <circle cx="65" cy="45" r="10" fill="none" stroke="#333" strokeWidth="2" />
              <path d="M45,45 L55,45" stroke="#333" strokeWidth="2" />
              <path d="M25,45 L15,42" stroke="#333" strokeWidth="2" />
              <path d="M75,45 L85,42" stroke="#333" strokeWidth="2" />
            </>
          )}
          {config.accessory === 'cap' && (
            <>
              <path
                d="M15,32 Q50,20 85,32 L85,25 Q50,15 15,25 Z"
                fill="#1976d2"
              />
              <path
                d="M15,32 Q-5,35 10,38 Q15,35 15,32"
                fill="#1976d2"
              />
            </>
          )}
        </svg>
      </div>

      {/* Category Tabs */}
      <div style={styles.tabs}>
        {[
          { id: 'skinTone', label: 'Skin' },
          { id: 'faceShape', label: 'Face' },
          { id: 'hairStyle', label: 'Hair' },
          { id: 'hairColor', label: 'Color' },
          { id: 'accessories', label: 'Extras' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...styles.tab,
              ...(activeTab === tab.id && styles.tabActive)
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Options */}
      <div style={styles.options}>
        {activeTab === 'skinTone' && (
          <div style={styles.colorGrid}>
            {AVATAR_OPTIONS.skinTone.map(option => (
              <button
                key={option.id}
                onClick={() => updateConfig('skinTone', option.id)}
                style={{
                  ...styles.colorOption,
                  backgroundColor: option.color,
                  ...(config.skinTone === option.id && styles.colorOptionSelected)
                }}
                title={option.name}
              />
            ))}
          </div>
        )}

        {activeTab === 'faceShape' && (
          <div style={styles.optionGrid}>
            {AVATAR_OPTIONS.faceShape.map(option => (
              <button
                key={option.id}
                onClick={() => updateConfig('faceShape', option.id)}
                style={{
                  ...styles.option,
                  ...(config.faceShape === option.id && styles.optionSelected)
                }}
              >
                <svg viewBox="0 0 100 100" style={styles.miniAvatar}>
                  <path d={option.path} fill={currentSkin.color} stroke="#ddd" strokeWidth="2" />
                </svg>
                <span>{option.name}</span>
              </button>
            ))}
          </div>
        )}

        {activeTab === 'hairStyle' && (
          <div style={styles.optionGrid}>
            {AVATAR_OPTIONS.hairStyle.map(option => (
              <button
                key={option.id}
                onClick={() => updateConfig('hairStyle', option.id)}
                style={{
                  ...styles.option,
                  ...(config.hairStyle === option.id && styles.optionSelected)
                }}
              >
                <svg viewBox="0 0 100 100" style={styles.miniAvatar}>
                  <path d={currentFace.path} fill={currentSkin.color} stroke="#ddd" strokeWidth="2" />
                  {option.path && <path d={option.path} fill={currentHairColor.color} />}
                </svg>
                <span>{option.name}</span>
              </button>
            ))}
          </div>
        )}

        {activeTab === 'hairColor' && (
          <div style={styles.colorGrid}>
            {AVATAR_OPTIONS.hairColor.map(option => (
              <button
                key={option.id}
                onClick={() => updateConfig('hairColor', option.id)}
                style={{
                  ...styles.colorOption,
                  backgroundColor: option.color,
                  ...(config.hairColor === option.id && styles.colorOptionSelected)
                }}
                title={option.name}
              />
            ))}
          </div>
        )}

        {activeTab === 'accessories' && (
          <div style={styles.optionGrid}>
            {AVATAR_OPTIONS.accessories.map(option => (
              <button
                key={option.id}
                onClick={() => updateConfig('accessory', option.id)}
                style={{
                  ...styles.option,
                  ...(config.accessory === option.id && styles.optionSelected)
                }}
              >
                <span style={styles.accessoryIcon}>
                  {option.id === 'none' && '❌'}
                  {option.id === 'headband' && '🎀'}
                  {option.id === 'glasses' && '👓'}
                  {option.id === 'cap' && '🧢'}
                </span>
                <span>{option.name}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px',
    padding: '16px',
  },
  preview: {
    width: '120px',
    height: '120px',
    backgroundColor: '#f5f5f5',
    borderRadius: '50%',
    overflow: 'hidden',
    border: '3px solid #2d5016',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
  },
  avatarSvg: {
    width: '100%',
    height: '100%',
  },
  tabs: {
    display: 'flex',
    gap: '4px',
    backgroundColor: '#f0f0f0',
    padding: '4px',
    borderRadius: '8px',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  tab: {
    padding: '8px 12px',
    border: 'none',
    backgroundColor: 'transparent',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
    color: '#666',
    transition: 'all 0.2s ease',
  },
  tabActive: {
    backgroundColor: 'white',
    color: '#2d5016',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  },
  options: {
    width: '100%',
    minHeight: '80px',
  },
  colorGrid: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
    flexWrap: 'wrap',
  },
  colorOption: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    border: '3px solid transparent',
    cursor: 'pointer',
    transition: 'transform 0.2s ease',
  },
  colorOptionSelected: {
    border: '3px solid #2d5016',
    transform: 'scale(1.1)',
  },
  optionGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))',
    gap: '8px',
  },
  option: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
    padding: '8px',
    border: '2px solid #eee',
    borderRadius: '8px',
    backgroundColor: 'white',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  optionSelected: {
    borderColor: '#2d5016',
    backgroundColor: '#e8f5e9',
  },
  miniAvatar: {
    width: '40px',
    height: '40px',
  },
  accessoryIcon: {
    fontSize: '24px',
  },
};
