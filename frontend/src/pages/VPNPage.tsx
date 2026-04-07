import { useState, useEffect } from 'react'
import {
  Box,
  Title,
  Paper,
  Table,
  Text,
  Badge,
  Loader,
  SimpleGrid,
  Tabs,
} from '@mantine/core'
import { IconLock } from '@tabler/icons-react'
import { api } from '../store/auth'
import { notifications } from '@mantine/notifications'

interface VPNTunnel {
  id: number
  device_id: number
  tunnel_name: string
  tunnel_type: string
  status: string
  local_endpoint: string
  remote_endpoint: string
  uptime: number
  bytes_encrypted: number
  bytes_decrypted: number
}

interface NHRPCache {
  id: number
  device_id: number
  protocol_ip: string
  nbma_ip: string
  entry_type: string
  remaining_time: number
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

function formatBytes(bytes: number): string {
  const gb = bytes / (1024 * 1024 * 1024)
  if (gb >= 1) return `${gb.toFixed(2)} GB`
  const mb = bytes / (1024 * 1024)
  if (mb >= 1) return `${mb.toFixed(2)} MB`
  const kb = bytes / 1024
  return `${kb.toFixed(2)} KB`
}

export default function VPNPage() {
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('tunnels')
  const [tunnels, setTunnels] = useState<VPNTunnel[]>([])
  const [nhrpCache, setNhrpCache] = useState<NHRPCache[]>([])
  const [summary, setSummary] = useState<any>(null)

  useEffect(() => {
    fetchVPNData()
  }, [])

  const fetchVPNData = async () => {
    try {
      const [tunnelsRes, nhrpRes, summaryRes] = await Promise.all([
        api.get('/vpn/tunnels'),
        api.get('/vpn/dmvpn/nhrp-cache'),
        api.get('/vpn/summary'),
      ])

      setTunnels(tunnelsRes.data)
      setNhrpCache(nhrpRes.data)
      setSummary(summaryRes.data)
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to load VPN data',
        color: 'red',
      })
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Box style={{ padding: 40, textAlign: 'center' }}>
        <Loader />
      </Box>
    )
  }

  const statusColors: Record<string, string> = {
    up: 'green',
    down: 'red',
    degraded: 'orange',
    unknown: 'gray',
  }

  return (
    <div>
      <Title order={2} mb="lg">VPN Monitoring</Title>

      <SimpleGrid cols={4} mb="lg">
        <Paper p="lg" radius="md">
          <Text c="dimmed" size="xs" tt="uppercase">Total Tunnels</Text>
          <Text fw={700} size="xl" mt="xs">{summary?.total_tunnels || 0}</Text>
        </Paper>
        <Paper p="lg" radius="md">
          <Text c="dimmed" size="xs" tt="uppercase">Tunnels Up</Text>
          <Text fw={700} size="xl" mt="xs" c="green">{summary?.tunnels_up || 0}</Text>
        </Paper>
        <Paper p="lg" radius="md">
          <Text c="dimmed" size="xs" tt="uppercase">Tunnels Down</Text>
          <Text fw={700} size="xl" mt="xs" c="red">{summary?.tunnels_down || 0}</Text>
        </Paper>
        <Paper p="lg" radius="md">
          <Text c="dimmed" size="xs" tt="uppercase">DMVPN Spokes</Text>
          <Text fw={700} size="xl" mt="xs">{summary?.dmvpn_spokes || 0}</Text>
        </Paper>
      </SimpleGrid>

      <Tabs value={activeTab} onChange={(v) => setActiveTab(v || 'tunnels')}>
        <Tabs.List>
          <Tabs.Tab value="tunnels">VPN Tunnels</Tabs.Tab>
          <Tabs.Tab value="dmvpn">DMVPN (NHRP)</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="tunnels" pt="md">
          <Paper shadow="sm" radius="md">
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Device</Table.Th>
                  <Table.Th>Tunnel Name</Table.Th>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Local Endpoint</Table.Th>
                  <Table.Th>Remote Endpoint</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Uptime</Table.Th>
                  <Table.Th>Traffic</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {tunnels.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={8} ta="center" py="xl">
                      <Text c="dimmed">No VPN tunnels configured</Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  tunnels.map((tunnel) => (
                    <Table.Tr key={tunnel.id}>
                      <Table.Td>Device #{tunnel.device_id}</Table.Td>
                      <Table.Td fw={500}>{tunnel.tunnel_name}</Table.Td>
                      <Table.Td>
                        <Badge variant="light" color="blue">
                          {tunnel.tunnel_type}
                        </Badge>
                      </Table.Td>
                      <Table.Td>{tunnel.local_endpoint || '-'}</Table.Td>
                      <Table.Td>{tunnel.remote_endpoint || '-'}</Table.Td>
                      <Table.Td>
                        <Badge color={statusColors[tunnel.status] || 'gray'}>
                          {tunnel.status}
                        </Badge>
                      </Table.Td>
                      <Table.Td>{formatUptime(tunnel.uptime)}</Table.Td>
                      <Table.Td>
                        <Text size="sm">
                          ↓ {formatBytes(tunnel.bytes_decrypted)}<br />
                          ↑ {formatBytes(tunnel.bytes_encrypted)}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ))
                )}
              </Table.Tbody>
            </Table>
          </Paper>
        </Tabs.Panel>

        <Tabs.Panel value="dmvpn" pt="md">
          <Paper shadow="sm" radius="md">
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Device</Table.Th>
                  <Table.Th>Protocol IP</Table.Th>
                  <Table.Th>NBMA IP</Table.Th>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Remaining Time</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {nhrpCache.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={5} ta="center" py="xl">
                      <Text c="dimmed">No NHRP cache entries</Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  nhrpCache.map((entry) => (
                    <Table.Tr key={entry.id}>
                      <Table.Td>Device #{entry.device_id}</Table.Td>
                      <Table.Td fw={500}>{entry.protocol_ip}</Table.Td>
                      <Table.Td>{entry.nbma_ip}</Table.Td>
                      <Table.Td>
                        <Badge variant="light" color={entry.entry_type === 'static' ? 'blue' : 'green'}>
                          {entry.entry_type}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        {entry.remaining_time > 0
                          ? `${Math.floor(entry.remaining_time / 60)}m ${entry.remaining_time % 60}s`
                          : 'Expired'}
                      </Table.Td>
                    </Table.Tr>
                  ))
                )}
              </Table.Tbody>
            </Table>
          </Paper>
        </Tabs.Panel>
      </Tabs>
    </div>
  )
}
