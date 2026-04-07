import { useState, useEffect } from 'react'
import {
  Box,
  Title,
  Paper,
  Table,
  Group,
  Button,
  Text,
  Badge,
  ActionIcon,
  Tooltip,
  Loader,
  SimpleGrid,
} from '@mantine/core'
import {
  IconDownload,
  IconRefresh,
  IconTrash,
  IconDatabase,
  IconClock,
} from '@tabler/icons-react'
import { api } from '../store/auth'
import { notifications } from '@mantine/notifications'
import dayjs from 'dayjs'

interface Backup {
  id: number
  device_id: number
  device_name: string
  backup_name: string
  backup_type: string
  status: string
  file_size: number
  created_at: string
  error_message?: string
}

interface BackupStats {
  total_backups: number
  successful_backups: number
  failed_backups: number
  total_size_bytes: number
}

function formatBytes(bytes: number): string {
  const gb = bytes / (1024 * 1024 * 1024)
  if (gb >= 1) return `${gb.toFixed(2)} GB`
  const mb = bytes / (1024 * 1024)
  if (mb >= 1) return `${mb.toFixed(2)} MB`
  return `${(bytes / 1024).toFixed(2)} KB`
}

export default function BackupPage() {
  const [backups, setBackups] = useState<Backup[]>([])
  const [stats, setStats] = useState<BackupStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)

  useEffect(() => {
    fetchBackups()
  }, [])

  const fetchBackups = async () => {
    try {
      const [backupsRes, statsRes] = await Promise.all([
        api.get('/backups?limit=50'),
        api.get('/backups/stats'),
      ])
      setBackups(backupsRes.data)
      setStats(statsRes.data)
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to load backups',
        color: 'red',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleTriggerBackup = async () => {
    if (!confirm('Trigger backup for all devices?')) return

    setTriggering(true)
    try {
      await api.post('/backups/trigger-all?backup_type=running_config')
      notifications.show({
        title: 'Success',
        message: 'Backup triggered for all devices',
        color: 'green',
      })
      setTimeout(fetchBackups, 5000)
    } catch (error: any) {
      notifications.show({
        title: 'Error',
        message: error.response?.data?.detail || 'Failed to trigger backup',
        color: 'red',
      })
    } finally {
      setTriggering(false)
    }
  }

  const handleDownload = async (backup: Backup) => {
    try {
      const response = await api.get(`/backups/${backup.id}/download`, {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', backup.backup_name)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to download backup',
        color: 'red',
      })
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this backup?')) return

    try {
      await api.delete(`/backups/${id}`)
      notifications.show({ title: 'Success', message: 'Backup deleted', color: 'green' })
      fetchBackups()
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to delete backup',
        color: 'red',
      })
    }
  }

  const statusColors: Record<string, string> = {
    success: 'green',
    failed: 'red',
    in_progress: 'blue',
    scheduled: 'gray',
  }

  return (
    <div>
      <Group justify="space-between" mb="lg">
        <Title order={2}>Device Backups</Title>
        <Group>
          <Button
            variant="outline"
            leftSection={<IconRefresh size={18} />}
            onClick={fetchBackups}
          >
            Refresh
          </Button>
          <Button
            leftSection={<IconDatabase size={18} />}
            onClick={handleTriggerBackup}
            loading={triggering}
          >
            Backup All Devices
          </Button>
        </Group>
      </Group>

      <SimpleGrid cols={4} mb="lg">
        <Paper p="lg" radius="md">
          <Text c="dimmed" size="xs" tt="uppercase">Total Backups</Text>
          <Text fw={700} size="xl" mt="xs">{stats?.total_backups || 0}</Text>
        </Paper>
        <Paper p="lg" radius="md">
          <Text c="dimmed" size="xs" tt="uppercase">Successful</Text>
          <Text fw={700} size="xl" mt="xs" c="green">{stats?.successful_backups || 0}</Text>
        </Paper>
        <Paper p="lg" radius="md">
          <Text c="dimmed" size="xs" tt="uppercase">Failed</Text>
          <Text fw={700} size="xl" mt="xs" c="red">{stats?.failed_backups || 0}</Text>
        </Paper>
        <Paper p="lg" radius="md">
          <Text c="dimmed" size="xs" tt="uppercase">Total Size</Text>
          <Text fw={700} size="xl" mt="xs">{formatBytes(stats?.total_size_bytes || 0)}</Text>
        </Paper>
      </SimpleGrid>

      <Paper shadow="sm" radius="md">
        {loading ? (
          <Box style={{ padding: 40, textAlign: 'center' }}>
            <Loader />
          </Box>
        ) : (
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Device</Table.Th>
                <Table.Th>Backup Name</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Size</Table.Th>
                <Table.Th>Created</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {backups.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={7} ta="center" py="xl">
                    <Text c="dimmed">No backups available. Click "Backup All Devices" to create backups.</Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                backups.map((backup) => (
                  <Table.Tr key={backup.id}>
                    <Table.Td fw={500}>{backup.device_name}</Table.Td>
                    <Table.Td>{backup.backup_name}</Table.Td>
                    <Table.Td>
                      <Badge variant="light" color="blue">
                        {backup.backup_type}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Badge color={statusColors[backup.status] || 'gray'}>
                        {backup.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{formatBytes(backup.file_size)}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <IconClock size={14} />
                        <Text size="sm">{dayjs(backup.created_at).format('MMM D, YYYY HH:mm')}</Text>
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Tooltip label="Download">
                          <ActionIcon
                            variant="light"
                            color="blue"
                            onClick={() => handleDownload(backup)}
                          >
                            <IconDownload size={16} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Delete">
                          <ActionIcon
                            variant="light"
                            color="red"
                            onClick={() => handleDelete(backup.id)}
                          >
                            <IconTrash size={16} />
                          </ActionIcon>
                        </Tooltip>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
    </div>
  )
}
