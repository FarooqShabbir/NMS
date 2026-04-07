import { useState, useEffect } from 'react'
import {
  Grid,
  Paper,
  Text,
  Group,
  RingProgress,
  SimpleGrid,
  Box,
  Title,
  Loader,
} from '@mantine/core'
import {
  IconServer,
  IconAlertTriangle,
  IconCheck,
} from '@tabler/icons-react'
import { api } from '../store/auth'
import { notifications } from '@mantine/notifications'

interface DeviceCount {
  total: number
  up: number
  down: number
  warning: number
  unknown: number
}

interface AlertSummary {
  total_alerts: number
  active_alerts: number
  critical_alerts: number
  warning_alerts: number
}

interface RoutingSummary {
  bgp_neighbors: number
  bgp_established: number
  ospf_neighbors: number
  ospf_full: number
}

function StatCard({ title, value, icon: Icon, color, subtitle }: any) {
  return (
    <Paper p="lg" radius="md" shadow="sm" style={{ border: '1px solid var(--mantine-color-gray-3)' }}>
      <Group justify="space-between">
        <div>
          <Text c="dimmed" size="xs" tt="uppercase" fw={700}>
            {title}
          </Text>
          <Text fw={700} size="xl" mt="xs">
            {value}
          </Text>
          {subtitle && (
            <Text size="xs" c="dimmed" mt="xs">
              {subtitle}
            </Text>
          )}
        </div>
        <Box
          style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            backgroundColor: `var(--mantine-color-${color}-light)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon size={24} color={`var(--mantine-color-${color})`} />
        </Box>
      </Group>
    </Paper>
  )
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)
  const [deviceCount, setDeviceCount] = useState<DeviceCount | null>(null)
  const [alertSummary, setAlertSummary] = useState<AlertSummary | null>(null)
  const [routingSummary, setRoutingSummary] = useState<RoutingSummary | null>(null)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      const [devicesRes, alertsRes, bgpRes, ospfRes] = await Promise.all([
        api.get('/devices/count'),
        api.get('/alerts/summary'),
        api.get('/routing/bgp/summary'),
        api.get('/routing/ospf/summary'),
      ])

      setDeviceCount(devicesRes.data)
      setAlertSummary(alertsRes.data)
      setRoutingSummary({
        bgp_neighbors: bgpRes.data.total_neighbors,
        bgp_established: bgpRes.data.established,
        ospf_neighbors: ospfRes.data.total_neighbors,
        ospf_full: ospfRes.data.full_adjacencies,
      })
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to load dashboard data',
        color: 'red',
      })
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Center style={{ height: '100%' }}>
        <Loader size="xl" />
      </Center>
    )
  }

  const uptimePercentage = deviceCount
    ? Math.round((deviceCount.up / deviceCount.total) * 100) || 0
    : 0

  return (
    <div>
      <Title order={2} mb="lg">Dashboard</Title>

      <SimpleGrid cols={4} mb="lg">
        <StatCard
          title="Total Devices"
          value={deviceCount?.total || 0}
          icon={IconServer}
          color="blue"
          subtitle={`${deviceCount?.up || 0} online`}
        />
        <StatCard
          title="Devices Up"
          value={deviceCount?.up || 0}
          icon={IconCheck}
          color="green"
          subtitle={`${uptimePercentage}% availability`}
        />
        <StatCard
          title="Devices Down"
          value={deviceCount?.down || 0}
          icon={IconAlertTriangle}
          color="red"
        />
        <StatCard
          title="Active Alerts"
          value={alertSummary?.active_alerts || 0}
          icon={IconAlertTriangle}
          color="orange"
          subtitle={`${alertSummary?.critical_alerts || 0} critical`}
        />
      </SimpleGrid>

      <Grid>
        <Grid.Col span={6}>
          <Paper p="lg" radius="md" shadow="sm">
            <Title order={4} mb="md">Device Status Overview</Title>
            <Group gap="xl" justify="center">
              <RingProgress
                size={180}
                thickness={18}
                roundCaps
                sections={[
                  {
                    value: uptimePercentage,
                    color: 'green',
                    tooltip: `${uptimePercentage}% Online`,
                  },
                ]}
                label={
                  <Center>
                    <Text fw={700} size="xl">
                      {uptimePercentage}%
                    </Text>
                  </Center>
                }
              />
              <div>
                <Group gap="sm" mb="xs">
                  <Box style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: 'var(--mantine-color-green)' }} />
                  <Text size="sm">Up: {deviceCount?.up}</Text>
                </Group>
                <Group gap="sm" mb="xs">
                  <Box style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: 'var(--mantine-color-red)' }} />
                  <Text size="sm">Down: {deviceCount?.down}</Text>
                </Group>
                <Group gap="sm" mb="xs">
                  <Box style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: 'var(--mantine-color-orange)' }} />
                  <Text size="sm">Warning: {deviceCount?.warning}</Text>
                </Group>
                <Group gap="sm">
                  <Box style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: 'var(--mantine-color-gray)' }} />
                  <Text size="sm">Unknown: {deviceCount?.unknown}</Text>
                </Group>
              </div>
            </Group>
          </Paper>
        </Grid.Col>

        <Grid.Col span={6}>
          <Paper p="lg" radius="md" shadow="sm">
            <Title order={4} mb="md">Routing Protocol Status</Title>
            <SimpleGrid cols={2}>
              <Paper p="md" radius="sm" bg="var(--mantine-color-gray-0)">
                <Text c="dimmed" size="xs" tt="uppercase">BGP Neighbors</Text>
                <Group justify="space-between" mt="sm">
                  <Text fw={700} size="xl">
                    {routingSummary?.bgp_established || 0}
                    <Text span c="dimmed" size="sm"> / {routingSummary?.bgp_neighbors || 0}</Text>
                  </Text>
                  <Text size="sm" c={routingSummary && routingSummary.bgp_established === routingSummary.bgp_neighbors ? 'green' : 'orange'}>
                    {routingSummary && routingSummary.bgp_established === routingSummary.bgp_neighbors ? 'All Established' : 'Some Down'}
                  </Text>
                </Group>
              </Paper>
              <Paper p="md" radius="sm" bg="var(--mantine-color-gray-0)">
                <Text c="dimmed" size="xs" tt="uppercase">OSPF Neighbors</Text>
                <Group justify="space-between" mt="sm">
                  <Text fw={700} size="xl">
                    {routingSummary?.ospf_full || 0}
                    <Text span c="dimmed" size="sm"> / {routingSummary?.ospf_neighbors || 0}</Text>
                  </Text>
                  <Text size="sm" c={routingSummary && routingSummary.ospf_full === routingSummary.ospf_neighbors ? 'green' : 'orange'}>
                    {routingSummary && routingSummary.ospf_full === routingSummary.ospf_neighbors ? 'Full Adjacency' : 'Issues'}
                  </Text>
                </Group>
              </Paper>
            </SimpleGrid>
          </Paper>
        </Grid.Col>
      </Grid>
    </div>
  )
}

function Center({ children }: any) {
  return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{children}</div>
}
