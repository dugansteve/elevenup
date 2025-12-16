import { useState, useMemo, useEffect } from 'react';
import { storage, linkHelpers, LINK_PLATFORMS } from '../data/sampleData';
import { useUser } from '../context/UserContext';

function LinkManager({ entityType, entityId, entityName, isOwner = false }) {
  const { canPerform } = useUser();
  const canAddLinksPermission = canPerform('canAddLinks');
  
  const [links, setLinks] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showManageModal, setShowManageModal] = useState(false);
  const [newLink, setNewLink] = useState({ platform: 'youtube', url: '', title: '' });
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  
  const user = storage.getUser();
  const blocked = storage.getBlockedLinks();
  const playerBlocks = blocked[entityId] || { blockedLinkIds: [], blockAllNew: false };

  // Load links
  useEffect(() => {
    loadLinks();
  }, [entityType, entityId, refreshKey]);

  const loadLinks = () => {
    let loadedLinks;
    if (entityType === 'player' && !isOwner) {
      loadedLinks = linkHelpers.getVisibleLinksForPlayer(entityId);
    } else {
      loadedLinks = linkHelpers.getLinksForEntity(entityType, entityId);
    }
    // Sort by popularity score descending
    loadedLinks.sort((a, b) => (b.popularityScore || 0) - (a.popularityScore || 0));
    setLinks(loadedLinks);
  };

  // Check if user can add links (must have permission AND not be blocked for player)
  const canAddLinks = canAddLinksPermission && (entityType !== 'player' || !linkHelpers.areNewLinksBlocked(entityId));

  // Handle adding a new link
  const handleAddLink = async (e) => {
    e.preventDefault();
    setError('');
    setIsVerifying(true);

    try {
      // Validate platform-specific URL
      const platform = LINK_PLATFORMS.find(p => p.id === newLink.platform);
      if (newLink.platform !== 'website' && !linkHelpers.matchesPlatform(newLink.url, newLink.platform)) {
        setError(`URL doesn't appear to be a valid ${platform.name} link`);
        setIsVerifying(false);
        return;
      }

      const result = await linkHelpers.addLink({
        entityType,
        entityId: String(entityId),
        platform: newLink.platform,
        url: newLink.url,
        title: newLink.title || `${entityName} on ${platform.name}`,
        addedBy: user?.name || 'Anonymous',
        addedByUserId: user?.id || 'anon',
      });

      if (result.success) {
        setNewLink({ platform: 'youtube', url: '', title: '' });
        setShowAddModal(false);
        setRefreshKey(k => k + 1);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('Failed to add link. Please try again.');
    }
    
    setIsVerifying(false);
  };

  // Handle clicking a link (track for popularity)
  const handleLinkClick = (link) => {
    const userId = user?.id || 'anon_' + Math.random().toString(36).substr(2, 9);
    linkHelpers.recordClick(link.id, userId);
    setRefreshKey(k => k + 1);
    // Open link in new tab
    window.open(link.url, '_blank', 'noopener,noreferrer');
  };

  // Handle rating a link
  const handleRate = (linkId, rating) => {
    const userId = user?.id || 'anon';
    linkHelpers.rateLink(linkId, userId, rating);
    setRefreshKey(k => k + 1);
  };

  // Handle deleting a link
  const handleDelete = (linkId) => {
    if (window.confirm('Are you sure you want to delete this link?')) {
      linkHelpers.deleteLink(linkId);
      setRefreshKey(k => k + 1);
    }
  };

  // Handle blocking a link (for player owners)
  const handleBlock = (linkId) => {
    linkHelpers.blockLinkForPlayer(entityId, linkId);
    setRefreshKey(k => k + 1);
  };

  // Handle unblocking a link
  const handleUnblock = (linkId) => {
    linkHelpers.unblockLinkForPlayer(entityId, linkId);
    setRefreshKey(k => k + 1);
  };

  // Handle toggling block all new links
  const handleToggleBlockAll = () => {
    linkHelpers.setBlockAllNewLinks(entityId, !playerBlocks.blockAllNew);
    setRefreshKey(k => k + 1);
  };

  // Get user's rating for a link
  const getUserRating = (link) => {
    const userId = user?.id || 'anon';
    return link.ratings[userId] || 0;
  };

  // Get platform info
  const getPlatform = (platformId) => {
    return LINK_PLATFORMS.find(p => p.id === platformId) || LINK_PLATFORMS[LINK_PLATFORMS.length - 1];
  };

  // Get all links including blocked ones (for management)
  const allLinks = useMemo(() => {
    return linkHelpers.getLinksForEntity(entityType, entityId)
      .sort((a, b) => (b.popularityScore || 0) - (a.popularityScore || 0));
  }, [entityType, entityId, refreshKey]);

  // Render stars for rating
  const renderStars = (link, interactive = true) => {
    const userRating = getUserRating(link);
    const stars = [];
    
    for (let i = 1; i <= 5; i++) {
      stars.push(
        <span
          key={i}
          onClick={(e) => {
            if (interactive) {
              e.stopPropagation();
              handleRate(link.id, i);
            }
          }}
          style={{
            cursor: interactive ? 'pointer' : 'default',
            color: i <= (userRating || link.averageRating) ? '#FFD700' : '#ddd',
            fontSize: '1.25rem',
            transition: 'transform 0.1s',
          }}
          onMouseEnter={(e) => interactive && (e.target.style.transform = 'scale(1.2)')}
          onMouseLeave={(e) => interactive && (e.target.style.transform = 'scale(1)')}
        >
          ★
        </span>
      );
    }
    
    return stars;
  };

  return (
    <div>
      {/* Header with Add Button */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '1rem'
      }}>
        <h3 style={{ 
          fontSize: '1.1rem', 
          fontWeight: '600', 
          color: 'var(--primary-green)',
          margin: 0
        }}>
          🔗 Links & Media
        </h3>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {isOwner && entityType === 'player' && (
            <button
              onClick={() => setShowManageModal(true)}
              className="btn btn-secondary"
              style={{ fontSize: '0.85rem', padding: '0.5rem 1rem' }}
            >
              ⚙️ Manage
            </button>
          )}
          {canAddLinks && (
            <button
              onClick={() => setShowAddModal(true)}
              className="btn btn-primary"
              style={{ fontSize: '0.85rem', padding: '0.5rem 1rem' }}
            >
              ➕ Add Link
            </button>
          )}
        </div>
      </div>

      {/* Block notice for player pages */}
      {entityType === 'player' && playerBlocks.blockAllNew && !isOwner && (
        <div style={{
          padding: '0.75rem',
          background: '#fff3e0',
          borderRadius: '8px',
          marginBottom: '1rem',
          fontSize: '0.9rem',
          color: '#e65100'
        }}>
          🔒 New links cannot be added to this player's page
        </div>
      )}

      {/* Links List */}
      {links.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '2rem',
          color: '#888'
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🔗</div>
          <div>No links yet. {canAddLinks && 'Be the first to add one!'}</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {links.map(link => {
            const platform = getPlatform(link.platform);
            const isBlocked = playerBlocks.blockedLinkIds?.includes(link.id);
            
            return (
              <div
                key={link.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '1rem',
                  background: isBlocked ? '#f5f5f5' : '#f8f9fa',
                  borderRadius: '10px',
                  border: `2px solid ${isBlocked ? '#e0e0e0' : 'transparent'}`,
                  opacity: isBlocked ? 0.6 : 1,
                  transition: 'all 0.2s ease',
                  cursor: 'pointer'
                }}
                onClick={() => !isBlocked && handleLinkClick(link)}
                onMouseEnter={(e) => {
                  if (!isBlocked) {
                    e.currentTarget.style.borderColor = platform.color;
                    e.currentTarget.style.transform = 'translateX(4px)';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = isBlocked ? '#e0e0e0' : 'transparent';
                  e.currentTarget.style.transform = 'translateX(0)';
                }}
              >
                {/* Platform Icon */}
                <div style={{
                  width: '50px',
                  height: '50px',
                  borderRadius: '10px',
                  background: platform.color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.5rem',
                  marginRight: '1rem',
                  flexShrink: 0
                }}>
                  {platform.icon}
                </div>

                {/* Link Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ 
                    fontWeight: '600', 
                    color: 'var(--text-dark)',
                    marginBottom: '0.25rem',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {link.title}
                  </div>
                  <div style={{ 
                    fontSize: '0.8rem', 
                    color: '#888',
                    display: 'flex',
                    gap: '1rem',
                    alignItems: 'center',
                    flexWrap: 'wrap'
                  }}>
                    <span style={{ color: platform.color, fontWeight: '600' }}>{platform.name}</span>
                    <span>Added by {link.addedBy}</span>
                  </div>
                </div>

                {/* Stats & Actions */}
                <div style={{ 
                  display: 'flex', 
                  flexDirection: 'column',
                  alignItems: 'flex-end',
                  gap: '0.5rem',
                  marginLeft: '1rem'
                }}>
                  {/* Rating */}
                  <div onClick={(e) => e.stopPropagation()} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {renderStars(link)}
                    <span style={{ fontSize: '0.8rem', color: '#888' }}>
                      ({link.totalRatings || 0})
                    </span>
                  </div>
                  
                  {/* Popularity */}
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '0.5rem',
                    fontSize: '0.8rem',
                    color: '#888'
                  }}>
                    <span>🔥 {link.popularityScore || 0}</span>
                    {isOwner && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(link.id);
                        }}
                        style={{
                          background: '#fee',
                          border: '1px solid #fcc',
                          color: '#c33',
                          padding: '0.25rem 0.5rem',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '0.75rem'
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>

                {/* External link icon */}
                <div style={{ marginLeft: '0.5rem', color: '#888' }}>↗</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Link Modal */}
      {showAddModal && (
        <div 
          className="modal-overlay" 
          onClick={() => setShowAddModal(false)}
        >
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Add Link</h2>
            </div>
            
            <form onSubmit={handleAddLink}>
              <div className="form-group">
                <label className="form-label">Platform *</label>
                <select
                  className="form-select"
                  value={newLink.platform}
                  onChange={(e) => setNewLink({...newLink, platform: e.target.value})}
                  required
                >
                  {LINK_PLATFORMS.map(platform => (
                    <option key={platform.id} value={platform.id}>
                      {platform.icon} {platform.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">URL *</label>
                <input
                  type="url"
                  className="form-input"
                  value={newLink.url}
                  onChange={(e) => setNewLink({...newLink, url: e.target.value})}
                  placeholder={getPlatform(newLink.platform).placeholder}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Title (optional)</label>
                <input
                  type="text"
                  className="form-input"
                  value={newLink.title}
                  onChange={(e) => setNewLink({...newLink, title: e.target.value})}
                  placeholder={`${entityName} highlights, profile, etc.`}
                />
              </div>

              {error && (
                <div style={{
                  padding: '0.75rem',
                  background: '#ffebee',
                  borderRadius: '8px',
                  color: '#c62828',
                  marginBottom: '1rem',
                  fontSize: '0.9rem'
                }}>
                  ⚠️ {error}
                </div>
              )}

              <div style={{
                padding: '0.75rem',
                background: '#e3f2fd',
                borderRadius: '8px',
                marginBottom: '1rem',
                fontSize: '0.85rem',
                color: '#1565c0'
              }}>
                ℹ️ Links are verified for safety and appropriateness before being posted.
              </div>

              <div className="modal-actions">
                <button 
                  type="button" 
                  onClick={() => setShowAddModal(false)} 
                  className="btn btn-secondary"
                  disabled={isVerifying}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="btn btn-primary"
                  disabled={isVerifying}
                >
                  {isVerifying ? 'Verifying...' : 'Add Link'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Manage Links Modal (for player owners) */}
      {showManageModal && isOwner && entityType === 'player' && (
        <div 
          className="modal-overlay" 
          onClick={() => setShowManageModal(false)}
        >
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Manage Links</h2>
            </div>
            
            {/* Block All Toggle */}
            <div style={{
              padding: '1rem',
              background: '#f8f9fa',
              borderRadius: '8px',
              marginBottom: '1.5rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                  🔒 Block New Links
                </div>
                <div style={{ fontSize: '0.85rem', color: '#666' }}>
                  Prevent others from adding new links to this page
                </div>
              </div>
              <button
                onClick={handleToggleBlockAll}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '8px',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: '600',
                  background: playerBlocks.blockAllNew ? '#c62828' : '#4caf50',
                  color: 'white'
                }}
              >
                {playerBlocks.blockAllNew ? 'Blocked' : 'Allowed'}
              </button>
            </div>

            {/* Links List */}
            <h4 style={{ marginBottom: '1rem', color: 'var(--primary-green)' }}>
              All Links ({allLinks.length})
            </h4>
            
            {allLinks.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#888' }}>
                No links to manage
              </div>
            ) : (
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {allLinks.map(link => {
                  const platform = getPlatform(link.platform);
                  const isBlocked = playerBlocks.blockedLinkIds?.includes(link.id);
                  
                  return (
                    <div
                      key={link.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '0.75rem',
                        background: isBlocked ? '#ffebee' : '#f8f9fa',
                        borderRadius: '8px',
                        marginBottom: '0.5rem'
                      }}
                    >
                      <div style={{
                        width: '36px',
                        height: '36px',
                        borderRadius: '8px',
                        background: platform.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginRight: '0.75rem',
                        flexShrink: 0
                      }}>
                        {platform.icon}
                      </div>
                      
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ 
                          fontWeight: '500',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis'
                        }}>
                          {link.title}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#888' }}>
                          by {link.addedBy}
                        </div>
                      </div>
                      
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        {isBlocked ? (
                          <button
                            onClick={() => handleUnblock(link.id)}
                            style={{
                              padding: '0.375rem 0.75rem',
                              borderRadius: '6px',
                              border: 'none',
                              cursor: 'pointer',
                              fontSize: '0.8rem',
                              background: '#4caf50',
                              color: 'white'
                            }}
                          >
                            Unblock
                          </button>
                        ) : (
                          <button
                            onClick={() => handleBlock(link.id)}
                            style={{
                              padding: '0.375rem 0.75rem',
                              borderRadius: '6px',
                              border: 'none',
                              cursor: 'pointer',
                              fontSize: '0.8rem',
                              background: '#ff9800',
                              color: 'white'
                            }}
                          >
                            Block
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(link.id)}
                          style={{
                            padding: '0.375rem 0.75rem',
                            borderRadius: '6px',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '0.8rem',
                            background: '#c62828',
                            color: 'white'
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="modal-actions" style={{ marginTop: '1.5rem' }}>
              <button 
                onClick={() => setShowManageModal(false)} 
                className="btn btn-secondary"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default LinkManager;
