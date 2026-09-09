import { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../store/useStore'
import {
  Phone, LayoutDashboard, Building2, BarChart3, Users,
  Settings, LogOut, Bell, ChevronDown, ChevronRight, Menu, User as UserIcon,
  TrendingUp, AlertCircle, CheckCircle, FileText, Activity,
  ClipboardList, CalendarCheck, ShieldCheck, Target, Megaphone, Cpu, Sparkles
} from 'lucide-react'

import EnroloLogo from './EnroloLogo'

// Main-branch admin: full org + CRM management.
const NAV_ORG = [
  { path: '/dashboard',                     label: 'Overview',              icon: LayoutDashboard },
  { path: '/dashboard/lead-manager',        label: 'Lead Allocation',       icon: Users },
  { path: '/dashboard/application-manager', label: 'AI Application Manager',icon: Cpu },
  { path: '/dashboard/funnel-analytics',     label: 'Funnel & Analytics',    icon: TrendingUp },
  { path: '/dashboard/conversion-strategy', label: 'Conversion Strategy',   icon: Sparkles },
  { path: '/dashboard/branches',            label: 'Branches',              icon: Building2 },
  { path: '/dashboard/appointments',        label: 'Appointments',          icon: CalendarCheck },
  { path: '/dashboard/competitive',         label: 'Competitive Intel',     icon: Target },
  { path: '/dashboard/live',                label: 'Priya Voice AI',        icon: Phone },
  { path: '/dashboard/qr-management',       label: 'QR Generator',         icon: Megaphone },
  { path: '/dashboard/audit',               label: 'Audit Log',             icon: ShieldCheck },
  { path: '/dashboard/profile',             label: 'Profile',               icon: UserIcon },
  { path: '/dashboard/settings',            label: 'Settings',              icon: Settings },
]


// Branch officer: split CRM modules.
const NAV_OFFICER = [
  { path: '/dashboard/lead-manager',        label: 'Lead Allocation',       icon: Users },
  { path: '/dashboard/application-manager', label: 'AI Application Manager',icon: Cpu },
  { path: '/dashboard/funnel-analytics',     label: 'Funnel & Analytics',    icon: TrendingUp },
  { path: '/dashboard/conversion-strategy', label: 'Conversion Strategy',   icon: Sparkles },
  { path: '/dashboard/appointments',        label: 'Appointments',          icon: CalendarCheck },
  { path: '/dashboard/audit',               label: 'Activity',              icon: ShieldCheck },
  { path: '/dashboard/profile',             label: 'Profile',               icon: UserIcon },
  { path: '/dashboard/settings',            label: 'Settings',              icon: Settings },
]

// Student: book + view campus visits.
const NAV_STUDENT = [
  { path: '/dashboard/student',  label: 'My Visits', icon: CalendarCheck },
  { path: '/dashboard/profile',  label: 'Profile',   icon: UserIcon },
  { path: '/dashboard/settings', label: 'Settings',  icon: Settings },
]

function buildNav(user) {
  if (user?.role === 'student') return NAV_STUDENT
  if (user?.role === 'officer') return NAV_OFFICER
  if (user?.role === 'college_admin') {
    return [
      { path: '/dashboard/lead-manager',        label: 'Lead Allocation',       icon: Users },
      { path: '/dashboard/application-manager', label: 'AI Application Manager',icon: Cpu },
      { path: '/dashboard/funnel-analytics',     label: 'Funnel & Analytics',    icon: TrendingUp },
      { path: '/dashboard/conversion-strategy', label: 'Conversion Strategy',   icon: Sparkles },
      { path: '/dashboard/appointments',        label: 'Appointments',          icon: CalendarCheck },
      { path: '/dashboard/audit',               label: 'Audit Log',             icon: ShieldCheck },
      { path: '/dashboard/profile',             label: 'Profile',               icon: UserIcon },
      { path: '/dashboard/settings',            label: 'Settings',              icon: Settings },
    ]
  }
  return NAV_ORG
}

const NOTIFICATIONS = [
  { icon: CheckCircle, color: '#7D9B76', title: 'Campaign completed', meta: 'Aditya University · 481 calls processed', time: '12 min ago' },
  { icon: TrendingUp,  color: '#7D9B76', title: 'Lead conversion up 24%', meta: 'Last 7 days vs previous week',          time: '2 hours ago' },
  { icon: FileText,    color: '#C8923A', title: 'New student report ready', meta: 'Naveen Reddy · MBA Marketing',         time: '5 hours ago' },
  { icon: AlertCircle, color: '#C8923A', title: 'Low connect rate detected', meta: 'Aditya Pharmacy College · 38%',       time: 'Yesterday' },
]

export default function DashboardLayout({ children }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, org, logout } = useStore()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [notifOpen, setNotifOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [expandedMenus, setExpandedMenus] = useState({ Analytics: true }) // Analytics auto-open
  const [unread, setUnread] = useState(NOTIFICATIONS.length)
  const notifRef = useRef(null)
  const userMenuRef = useRef(null)

  useEffect(() => {
    const onDoc = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target))   setNotifOpen(false)
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) setUserMenuOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const handleLogout = () => { logout(); navigate('/') }
  const goToProfile = () => navigate('/dashboard/profile')

  const toggleSubmenu = (label) => {
    setExpandedMenus(prev => ({ ...prev, [label]: !prev[label] }))
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#FBFBFA', overflow: 'hidden' }}>
      {/* ============================ SIDEBAR ============================ */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.aside
            initial={{ x: -260 }} animate={{ x: 0 }} exit={{ x: -260 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            style={{ width: 240, background: '#FFFFFF', borderRight: '1px solid #E8E8E8', display: 'flex', flexDirection: 'column', flexShrink: 0, overflowY: 'auto' }}>

            <div style={{ padding: '20px 16px 16px', borderBottom: '1px solid #E8E8E8' }}>
              <div style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', padding: '2px 0' }} onClick={() => navigate('/')}>
                <EnroloLogo height={32} />
              </div>
              {(user?.orgName || org?.name) && (
                <div style={{ marginTop: 12, padding: '8px 10px', background: '#F1F5EE', borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: '#7A7A7A', marginBottom: 2, fontWeight: 500 }}>
                    {user?.role === 'college_admin' ? 'College' : 'Organisation'}
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#2C2C2C', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {user?.role === 'college_admin' ? (user.collegeName || user.orgName) : (user?.orgName || org?.name)}
                  </div>
                  {user?.role === 'college_admin' && user?.orgName && (
                    <div style={{ fontSize: 10, color: '#7A7A7A', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      part of {user.orgName}
                    </div>
                  )}
                </div>
              )}
            </div>

            <nav style={{ padding: '12px 8px', flex: 1 }}>
              <div style={{ fontSize: 11, color: '#A0A0A0', fontWeight: 600, padding: '6px 8px', letterSpacing: 0.6, textTransform: 'uppercase' }}>Navigation</div>
              {buildNav(user).map((item, i) => {
                // Item with Sub-branch
                if (item.children) {
                  const isChildActive = item.children.some(c => location.pathname === c.path)
                  const isOpen = expandedMenus[item.label] ?? isChildActive
                  const Icon = item.icon

                  return (
                    <div key={item.label} style={{ marginBottom: 4 }}>
                      <div
                        className={`sidebar-item ${isChildActive ? 'active' : ''}`}
                        onClick={() => toggleSubmenu(item.label)}
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                           <Icon size={16} />
                          <span>{item.label}</span>
                        </div>
                        {isOpen ? <ChevronDown size={14} color="#7A7A7A" /> : <ChevronRight size={14} color="#7A7A7A" />}
                      </div>

                      {isOpen && (
                        <div style={{ paddingLeft: 24, marginTop: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                          {item.children.map(sub => {
                            const isSubActive = location.pathname === sub.path
                            return (
                              <div
                                key={sub.path}
                                onClick={() => navigate(sub.path)}
                                style={{
                                  padding: '7px 12px',
                                  borderRadius: 8,
                                  fontSize: 13,
                                  fontWeight: isSubActive ? 700 : 500,
                                  color: isSubActive ? '#7D9B76' : '#5A5A5A',
                                  background: isSubActive ? '#F1F5EE' : 'transparent',
                                  cursor: 'pointer',
                                  transition: 'all 0.15s'
                                }}
                              >
                                • {sub.label}
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )
                }

                // Normal Nav Item
                const isActive = item.path === '/dashboard'
                  ? location.pathname === '/dashboard'
                  : location.pathname === item.path || location.pathname.startsWith(item.path + '/')
                const Icon = item.icon

                return (
                  <motion.div
                    key={item.path}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className={`sidebar-item ${isActive ? 'active' : ''}`}
                    onClick={() => navigate(item.path)} style={{ marginBottom: 2 }}>
                    <Icon size={16} />
                    {item.label}
                  </motion.div>
                )
              })}
            </nav>

            <div style={{ padding: '12px 8px', borderTop: '1px solid #E8E8E8' }}>
              <div onClick={goToProfile}
                style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 10, cursor: 'pointer', transition: 'background 0.2s' }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#F1F5EE'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                title="View profile">
                <div style={{ width: 32, height: 32, background: user?.avatar ? `url(${user.avatar}) center/cover` : '#7D9B76', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 600, color: 'white', flexShrink: 0 }}>
                  {!user?.avatar && (user?.name?.[0]?.toUpperCase() || 'U')}
                </div>
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#2C2C2C', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user?.name}</div>
                  <div style={{ fontSize: 11, color: '#7A7A7A', textTransform: 'capitalize' }}>{(user?.role || '').replace('_', ' ')}</div>
                </div>
              </div>
              <div className="sidebar-item" onClick={handleLogout} style={{ color: '#9B2C2C', marginTop: 4 }}>
                <LogOut size={16} /> Logout
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* ============================ MAIN ============================ */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <header style={{ height: 60, background: '#FFFFFF', borderBottom: '1px solid #E8E8E8', display: 'flex', alignItems: 'center', padding: '0 24px', gap: 16, flexShrink: 0 }}>
          <button onClick={() => setSidebarOpen(p => !p)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#5A5A5A', padding: 4, borderRadius: 6, transition: 'background 0.2s' }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#F1F5EE'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
            <Menu size={20} />
          </button>

          <div style={{ flex: 1 }} />

          {/* Notifications */}
          <div ref={notifRef} style={{ position: 'relative' }}>
            <button onClick={() => setNotifOpen(p => !p)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#5A5A5A', padding: 6, borderRadius: 8, position: 'relative' }}>
              <Bell size={20} />
              {unread > 0 && (
                <span style={{ position: 'absolute', top: 4, right: 4, background: '#C8923A', color: 'white', fontSize: 10, fontWeight: 700, borderRadius: 99, width: 16, height: 16, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {unread}
                </span>
              )}
            </button>

            {notifOpen && (
              <div style={{ position: 'absolute', right: 0, top: 44, width: 320, background: '#FFFFFF', border: '1px solid #E8E8E8', borderRadius: 14, boxShadow: '0 12px 32px rgba(0,0,0,0.1)', zIndex: 100, overflow: 'hidden' }}>
                <div style={{ padding: '14px 16px', borderBottom: '1px solid #E8E8E8', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 14, color: '#2C2C2C' }}>Notifications</span>
                  {unread > 0 && (
                    <button onClick={() => setUnread(0)} style={{ background: 'none', border: 'none', color: '#7D9B76', fontSize: 12, cursor: 'pointer', fontWeight: 500 }}>
                      Mark all as read
                    </button>
                  )}
                </div>
                <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                  {NOTIFICATIONS.map((n, i) => {
                    const Icon = n.icon
                    return (
                      <div key={i} style={{ padding: '12px 16px', borderBottom: i < NOTIFICATIONS.length - 1 ? '1px solid #F1F5EE' : 'none', display: 'flex', gap: 12 }}>
                        <div style={{ width: 28, height: 28, borderRadius: 8, background: `${n.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 2 }}>
                          <Icon size={14} color={n.color} />
                        </div>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 600, color: '#2C2C2C' }}>{n.title}</div>
                          <div style={{ fontSize: 12, color: '#5A5A5A', marginTop: 2 }}>{n.meta}</div>
                          <div style={{ fontSize: 11, color: '#A0A0A0', marginTop: 4 }}>{n.time}</div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Content View */}
        <main style={{ flex: 1, overflowY: 'auto', padding: '28px 40px 80px', boxSizing: 'border-box' }}>
          {children}
        </main>
      </div>
    </div>
  )
}
