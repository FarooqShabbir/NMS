import { useState, useEffect } from 'react'
import {
  Box,
  Title,
  Paper,
  Table,
  Group,
  Text,
  Badge,
  ActionIcon,
  Tooltip,
  Loader,
  SimpleGrid,
  Tabs,
} from '@mantine/core'
import { IconCheck, IconX } from '@tabler/icons-react'
import { api } from '../store/auth'
import { notifications } from '@mantine/notifications'
import dayjs from 'dayjs'

interface Alert {
  id: number
  device_id?: number
  device_name?: string
  alert_type: string
  severity: string
  status: string
  title: string
  message: string
  triggered_at: string
  acknowledged_at?: string
  acknowledged_by?: string
}

interface AlertSummary {
  total_alerts: number
  active_alerts: number
  critical_alerts: number
  warning_alerts: number
  alerts_by_type: Record<string, number>
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [summary, setSummary] = useState<AlertSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('active')

  useEffect(() => {
    fetchAlerts()
  }, [])

  const fetchAlerts = async () => {
    try {
      const [alertsRes, summaryRes] = await Promise.all([
        api.get(`/alerts?status=${activeTab === 'active' ? 'active' : ''}&limit=100`),
        api.get('/alerts/summary'),
      ])
      setAlerts(alertsRes.data)
      setSummary(summaryRes.data)
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to load alerts',
        color: 'red',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleAcknowledge = async (id: number) => {
    try {
      await api.put(`/alerts/${id}/acknowledge`, { acknowledgment_note: 'Acknowledged from UI' })
      notifications.show({ title: 'Success', message: 'Alert acknowledged', color: 'green' })
      fetchAlerts()
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to acknowledge alert',
        color: 'red',
      })
    }
  }

  const handleResolve = async (id: number) => {
    try {
      await api.put(`/alerts/${id}/resolve`, { acknowledgment_note: 'Resolved from UI' })
      notifications.show({ title: 'Success', message: 'Alert resolved', color: 'green' })
      fetchAlerts()
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to resolve alert',
        color: 'red',
      })
    }
  }

  const severityColors: Record<string, string> = {
    emergency: 'red',
    critical: 'red',
    warning: 'orange',
    info: 'blue',
  }

  const statusColors: Record<string, string> = {
    active: 'red',
    acknowledged: 'orange',
    resolved: 'green',
  }

  return (
    <div>
      <Title order={2} mb="lg">Alerts</Title>

      <SimpleGrid cols={4} mb="lg">
        <Paper p="lg" radius="md">
          <Text c="dimmed" size="xs" tt="uppercase">Total Alerts</Text>
          <Text fw={700} size="xl" mt="xs">{summary?.total_alerts || 0}</Text>
        </Paper>
        <Paper p="lg" radius="md">
          <Text c="dimmed" size="xs" tt="uppercase">Active</Text>
          <Text fw={700} size="xl" mt="xs" c="red">{summary?.active_alerts || 0}</Text>
        </Paper>
        <Paper p="lg" radius="md">
          <Text c="dimmed" size="xs" tt="uppercase">Critical</Text>
          <Text fw={700} size="xl" mt="xs" c="red">{summary?.critical_alerts || 0}</Text>
        </Paper>
        <Paper p="lg" radius="md">
          <Text c="dimmed" size="xs" tt="uppercase">Warning</Text>
          <Text fw={700} size="xl" mt="xs" c="orange">{summary?.warning_alerts || 0}</Text>
        </Paper>
      </SimpleGrid>

      <Tabs value={activeTab} onChange={(v) => { setActiveTab(v || 'active'); fetchAlerts() }}>
        <Tabs.List>
          <Tabs.Tab value="active">Active</Tabs.Tab>
          <Tabs.Tab value="acknowledged">Acknowledged</Tabs.Tab>
          <Tabs.Tab value="resolved">Resolved</Tabs.Tab>
          <Tabs.Tab value="all">All</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value={activeTab} pt="md">
          <Paper shadow="sm" radius="md">
            {loading ? (
              <Box style={{ padding: 40, textAlign: 'center' }}>
                <Loader />
              </Box>
            ) : (
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Severity</Table.Th>
                    <Table.Th>Device</Table.Th>
                    <Table.Th>Title</Table.Th>
                    <Table.Th>Type</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Triggered</Table.Th>
                    <Table.Th>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {alerts.length === 0 ? (
                    <Table.Tr>
                      <Table.Td colSpan={7} ta="center" py="xl">
                        <Text c="dimmed">No alerts in this category</Text>
                      </Table.Td>
                    </Table.Tr>
                  ) : (
                    alerts.map((alert) => (
                      <Table.Tr key={alert.id}>
                        <Table.Td>
                          <Badge color={severityColors[alert.severity] || 'gray'}>
                            {alert.severity}
                          </Badge>
                        </Table.Td>
                        <Table.Td fw={500}>{alert.device_name || 'N/A'}</Table.Td>
                        <Table.Td>{alert.title}</Table.Td>
                        <Table.Td>
                          <Badge variant="light" color="gray">
                            {alert.alert_type.replace(/_/g, ' ')}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Badge color={statusColors[alert.status] || 'gray'}>
                            {alert.status}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm">{dayjs(alert.triggered_at).format('MMM D, HH:mm')}</Text>
                        </Table.Td>
                        <Table.Td>
                          {alert.status === 'active' && (
                            <Group gap="xs">
                              <Tooltip label="Acknowledge">
                                <ActionIcon
                                  variant="light"
                                  color="blue"
                                  onClick={() => handleAcknowledge(alert.id)}
                                >
                                  <IconCheck size={16} />
                                </ActionIcon>
                              </Tooltip>
                              <Tooltip label="Resolve">
                                <ActionIcon
                                  variant="light"
                                  color="green"
                                  onClick={() => handleResolve(alert.id)}
                                >
                                  <IconX size={16} />
                                </ActionIcon>
                              </Tooltip>
                            </Group>
                          )}
                        </Table.Td>
                      </Table.Tr>
                    ))
                  )}
                </Table.Tbody>
              </Table>
            )}
          </Paper>
        </Tabs.Panel>
      </Tabs>
    </div>
  )
}
