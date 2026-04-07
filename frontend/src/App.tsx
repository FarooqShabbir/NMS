import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { AppShell, Group, Text, Box, Divider } from '@mantine/core'
import {
  IconDashboard,
  IconServer,
  IconRouter,
  IconLock,
  IconDatabase,
  IconAlertTriangle,
  IconSettings,
} from '@tabler/icons-react'

import DashboardPage from './pages/DashboardPage'
import DevicesPage from './pages/DevicesPage'
import RoutingPage from './pages/RoutingPage'
import VPNPage from './pages/VPNPage'
import BackupPage from './pages/BackupPage'
import AlertsPage from './pages/AlertsPage'
import { useAuth } from './store/auth'
import LoginPage from './pages/LoginPage'

function NavButton({ icon: Icon, label, active, onClick }: any) {
  return (
    <Box
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '10px 14px',
        borderRadius: '8px',
        cursor: 'pointer',
        backgroundColor: active ? 'var(--mantine-color-blue-light)' : 'transparent',
        color: active ? 'var(--mantine-color-blue)' : 'var(--mantine-color-gray-7)',
      }}
    >
      <Icon size={18} />
      <Text size="sm" fw={500}>{label}</Text>
    </Box>
  )
}

function AppContent() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  if (!user) {
    return <LoginPage />
  }

  const navLinks = [
    { icon: IconDashboard, label: 'Dashboard', path: '/dashboard' },
    { icon: IconServer, label: 'Devices', path: '/devices' },
    { icon: IconRouter, label: 'Routing', path: '/routing' },
    { icon: IconLock, label: 'VPN', path: '/vpn' },
    { icon: IconDatabase, label: 'Backups', path: '/backups' },
    { icon: IconAlertTriangle, label: 'Alerts', path: '/alerts' },
  ]

  return (
    <AppShell
      navbar={{ width: 220, breakpoint: 'sm', collapsed: { mobile: true } }}
      header={{ height: 60 }}
      padding="md"
    >
      <AppShell.Header h={60} px="md" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Group gap="sm">
          <Box style={{ width: 36, height: 36, borderRadius: 8, background: 'linear-gradient(135deg, #228be6, #15aabf)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <IconRouter size={20} color="white" />
          </Box>
          <div>
            <Text fw={700} size="lg">NMS</Text>
            <Text size="xs" c="dimmed">Network Monitoring</Text>
          </div>
        </Group>
        <Text size="sm" c="dimmed">{user.username}</Text>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <Box style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {navLinks.map((link) => (
            <NavButton
              key={link.path}
              icon={link.icon}
              label={link.label}
              active={location.pathname === link.path || (link.path === '/dashboard' && location.pathname === '/')}
              onClick={() => navigate(link.path)}
            />
          ))}
        </Box>
        <Divider my="sm" />
        <NavButton
          icon={IconSettings}
          label="Settings"
          active={location.pathname === '/settings'}
          onClick={() => navigate('/settings')}
        />
      </AppShell.Navbar>

      <AppShell.Main>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/devices" element={<DevicesPage />} />
          <Route path="/routing" element={<RoutingPage />} />
          <Route path="/vpn" element={<VPNPage />} />
          <Route path="/backups" element={<BackupPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  )
}

import { AuthProvider } from './store/auth'

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
