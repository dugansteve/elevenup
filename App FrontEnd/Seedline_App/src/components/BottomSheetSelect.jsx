import { useState, useMemo } from 'react';

// Check if ElevenUp theme is active (light theme with green-cyan accents)
const isElevenUpTheme = () => document.body.classList.contains('elevenup-theme');

/**
 * Mobile-friendly bottom sheet select component
 * Replaces native <select> elements with a tap-to-open modal with button grid
 *
 * Props:
 * - label: The label to display above the button
 * - value: Current selected value
 * - displayValue: Text to display on the button (optional, defaults to value)
 * - options: Array of options, can be:
 *   - Simple: [{ value: 'x', label: 'X' }, ...]
 *   - Grouped: [{ group: 'Group Name', options: [{ value: 'x', label: 'X' }, ...] }, ...]
 * - onChange: Callback when value changes
 * - placeholder: Placeholder text when no value selected
 * - className: Additional CSS class for the button
 */
function BottomSheetSelect({
  label,
  value,
  displayValue,
  options,
  onChange,
  placeholder = 'Select...',
  className = ''
}) {
  const [isOpen, setIsOpen] = useState(false);

  // Determine if options are grouped (check if ANY item has a group, not just the first)
  const isGrouped = options.length > 0 && options.some(opt => opt.group !== undefined);

  // Count total options for grid sizing
  const getTotalOptions = () => {
    if (isGrouped) {
      // Count both non-grouped items and items within groups
      return options.reduce((sum, item) => {
        if (item.group && item.options) {
          return sum + item.options.length;
        } else if (item.value !== undefined) {
          return sum + 1; // Non-grouped item like "All"
        }
        return sum;
      }, 0);
    }
    return options.length;
  };

  // Find the display text for current value
  const getDisplayText = () => {
    if (displayValue) return displayValue;
    if (!value) return placeholder;

    if (isGrouped) {
      for (const group of options) {
        if (!group.options) continue;
        const found = group.options.find(opt => opt.value === value);
        if (found) return found.label;
      }
      // Check non-grouped items too
      const nonGrouped = options.find(opt => !opt.group && opt.value === value);
      if (nonGrouped) return nonGrouped.label;
    } else {
      const found = options.find(opt => opt.value === value);
      if (found) return found.label;
    }
    return value;
  };

  const handleSelect = (selectedValue) => {
    onChange(selectedValue);
    setIsOpen(false);
  };

  // Theme-aware colors - ElevenUp uses light theme with green-cyan accents
  const elevenUp = isElevenUpTheme();
  const themeColors = useMemo(() => ({
    bg: 'white',
    bgSelected: elevenUp ? 'rgba(0, 200, 83, 0.15)' : '#e8f5e9',
    bgHeader: 'white',
    border: '#ddd',
    borderSelected: elevenUp ? '#00C853' : 'var(--primary-green)',
    text: '#333',
    textSelected: elevenUp ? '#00C853' : 'var(--primary-green)',
    textMuted: '#888',
    overlay: 'rgba(0, 0, 0, 0.5)',
    shadow: '0 10px 40px rgba(0,0,0,0.2)'
  }), [elevenUp]);

  // Button style for grid items
  const getButtonStyle = (isSelected) => ({
    padding: '0.5rem 0.75rem',
    border: isSelected ? `2px solid ${themeColors.borderSelected}` : `1px solid ${themeColors.border}`,
    borderRadius: '8px',
    background: isSelected ? themeColors.bgSelected : themeColors.bg,
    fontSize: '0.85rem',
    cursor: 'pointer',
    fontWeight: isSelected ? '600' : '400',
    color: isSelected ? themeColors.textSelected : themeColors.text,
    textAlign: 'center',
    transition: 'all 0.15s ease',
    minWidth: '60px'
  });

  const renderOptions = () => {
    const totalOptions = getTotalOptions();
    // Use more columns for many options (like states)
    const gridColumns = totalOptions > 20 ? 'repeat(auto-fill, minmax(70px, 1fr))'
                      : totalOptions > 10 ? 'repeat(auto-fill, minmax(90px, 1fr))'
                      : 'repeat(auto-fill, minmax(100px, 1fr))';

    if (isGrouped) {
      return options.map((item, index) => {
        // Handle non-grouped items (like "All" option)
        if (!item.group && item.value !== undefined) {
          return (
            <button
              key={item.value}
              onClick={() => handleSelect(item.value)}
              style={{
                ...getButtonStyle(value === item.value),
                gridColumn: '1 / -1',
                marginBottom: '0.5rem',
                background: value === item.value ? themeColors.bgSelected : '#f0f0f0',
                fontWeight: '600'
              }}
            >
              {item.label}
            </button>
          );
        }

        if (!item.group) return null;

        return (
          <div key={index} style={{ marginBottom: '1rem' }}>
            {/* Group Header */}
            <div style={{
              padding: '0.5rem 0',
              fontSize: '0.75rem',
              fontWeight: '600',
              color: themeColors.textMuted,
              textTransform: 'uppercase',
              borderBottom: `1px solid ${themeColors.border}`,
              marginBottom: '0.5rem'
            }}>
              {item.group}
            </div>
            {/* Group Options Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: gridColumns,
              gap: '0.5rem'
            }}>
              {item.options?.map((option) => (
                <button
                  key={option.value}
                  onClick={() => handleSelect(option.value)}
                  style={getButtonStyle(value === option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        );
      });
    } else {
      return (
        <div style={{
          display: 'grid',
          gridTemplateColumns: gridColumns,
          gap: '0.5rem'
        }}>
          {options.map((option) => (
            <button
              key={option.value}
              onClick={() => handleSelect(option.value)}
              style={getButtonStyle(value === option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      );
    }
  };

  return (
    <>
      {/* Trigger Button */}
      <button
        className={`filter-select mobile-filter-btn ${className}`}
        onClick={() => setIsOpen(true)}
        style={{
          textAlign: 'left',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: themeColors.bg,
          color: themeColors.text,
          border: `2px solid ${themeColors.border}`
        }}
      >
        <span style={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          flex: 1
        }}>
          {getDisplayText()}
        </span>
        <span style={{ marginLeft: '0.5rem', opacity: 0.6, flexShrink: 0 }}>▼</span>
      </button>

      {/* Modal with Button Grid */}
      {isOpen && (
        <div
          className="bottom-sheet-overlay"
          onClick={() => setIsOpen(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: themeColors.overlay,
            zIndex: 3000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem'
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: themeColors.bgHeader,
              borderRadius: '16px',
              width: '100%',
              maxWidth: '600px',
              maxHeight: '85vh',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: themeColors.shadow,
              border: '1px solid #e0e0e0'
            }}
          >
            {/* Header */}
            <div style={{
              padding: '1rem 1.25rem',
              borderBottom: `1px solid ${themeColors.border}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexShrink: 0
            }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600', color: elevenUp ? '#00C853' : 'var(--primary-green)' }}>
                {label ? `Select ${label}` : 'Select Option'}
              </h3>
              <button
                onClick={() => setIsOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '1.5rem',
                  cursor: 'pointer',
                  color: themeColors.textMuted,
                  padding: '0.25rem',
                  lineHeight: 1
                }}
              >
                ×
              </button>
            </div>

            {/* Options Grid */}
            <div style={{
              flex: 1,
              overflowY: 'auto',
              padding: '1rem 1.25rem',
              background: themeColors.bgHeader
            }}>
              {renderOptions()}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default BottomSheetSelect;
