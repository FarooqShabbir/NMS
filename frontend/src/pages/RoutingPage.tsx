import { useState, useEffect } from 'react'
import {
  Box,
  Title,
  Paper,
  Table,
  Group,
  Text,
  Badge,
  Tabs,
  Loader,
  SimpleGrid,
} from '@mantine/core'
import { IconRouter, IconNetwork } from '@tabler/icons-react'
import { api } from '../store/auth'
import { notifications } from '@mantine/notifications'

interface BGPNeighbor {
  id: number
  device_id: number
  neighbor_ip: string
  neighbor_as: number
  local_as: number
  state: string
  prefixes_received: number
  uptime: number
}

interface OSPFNeighbor {
  id: number
  device_id: number
  neighbor_ip: string
  neighbor_id: string
  state: string
  area_id: string
  uptime: number
}

interface EIGRPNeighbor {
  id: number
  device_id: number
  neighbor_ip: string
  autonomous_system: number
  uptime: number
  state: string
}

const bgpStateColors: Record<string, string> = {
  established: 'green',
  idle: 'gray',
  connect: 'orange',
  active: 'orange',
  open_sent: 'yellow',
  open_confirm: 'yellow',
}

const ospfStateColors: Record<string, string> = {
  full: 'green',
  'two_way': 'blue',
  exchange: 'yellow',
  loading: 'yellow',
  ex_start: 'orange',
  init: 'orange',
  down: 'red',
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

export default function RoutingPage() {
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('bgp')
  const [bgpNeighbors, setBgpNeighbors] = useState<BGPNeighbor[]>([])
  const [ospfNeighbors, setOspfNeighbors] = useState<OSPFNeighbor[]>([])
  const [eigrpNeighbors, setEigrpNeighbors] = useState<EIGRPNeighbor[]>([])
  const [summaries, setSummaries] = useState<any>({})

  useEffect(() => {
    fetchRoutingData()
  }, [])

  const fetchRoutingData = async () => {
    try {
      const [bgpRes, ospfRes, eigrpRes, bgpSum, ospfSum] = await Promise.all([
        api.get('/routing/bgp/neighbors'),
        api.get('/routing/ospf/neighbors'),
        api.get('/routing/eigrp/neighbors'),
        api.get('/routing/bgp/summary'),
        api.get('/routing/ospf/summary'),
      ])

      setBgpNeighbors(bgpRes.data)
      setOspfNeighbors(ospfRes.data)
      setEigrpNeighbors(eigrpRes.data)
      setSummaries({ bgp: bgpSum.data, ospf: ospfSum.data })
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to load routing data',
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

  return (
    <div>
      <Title order={2} mb="lg">Routing Protocols</Title>

      <SimpleGrid cols={3} mb="lg">
        <Paper p="lg" radius="md">
          <Group gap="sm">
            <IconRouter size={24} color="var(--mantine-color-blue)" />
            <div>
              <Text c="dimmed" size="xs">BGP Neighbors</Text>
              <Text fw={700} size="lg">
                {summaries.bgp?.established || 0} / {summaries.bgp?.total_neighbors || 0}
              </Text>
            </div>
          </Group>
        </Paper>
        <Paper p="lg" radius="md">
          <Group gap="sm">
            <IconNetwork size={24} color="var(--mantine-color-green)" />
            <div>
              <Text c="dimmed" size="xs">OSPF Neighbors</Text>
              <Text fw={700} size="lg">
                {summaries.ospf?.full_adjacencies || 0} / {summaries.ospf?.total_neighbors || 0}
              </Text>
            </div>
          </Group>
        </Paper>
        <Paper p="lg" radius="md">
          <Group gap="sm">
            <IconRouter size={24} color="var(--mantine-color-orange)" />
            <div>
              <Text c="dimmed" size="xs">EIGRP Neighbors</Text>
              <Text fw={700} size="lg">
                {eigrpNeighbors.length}
              </Text>
            </div>
          </Group>
        </Paper>
      </SimpleGrid>

      <Tabs value={activeTab} onChange={(v) => setActiveTab(v || 'bgp')}>
        <Tabs.List>
          <Tabs.Tab value="bgp">BGP</Tabs.Tab>
          <Tabs.Tab value="ospf">OSPF</Tabs.Tab>
          <Tabs.Tab value="eigrp">EIGRP</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="bgp" pt="md">
          <Paper shadow="sm" radius="md">
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Device</Table.Th>
                  <Table.Th>Neighbor IP</Table.Th>
                  <Table.Th>Local AS</Table.Th>
                  <Table.Th>Remote AS</Table.Th>
                  <Table.Th>State</Table.Th>
                  <Table.Th>Prefixes</Table.Th>
                  <Table.Th>Uptime</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {bgpNeighbors.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={7} ta="center" py="xl">
                      <Text c="dimmed">No BGP neighbors configured</Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  bgpNeighbors.map((neighbor) => (
                    <Table.Tr key={neighbor.id}>
                      <Table.Td>Device #{neighbor.device_id}</Table.Td>
                      <Table.Td fw={500}>{neighbor.neighbor_ip}</Table.Td>
                      <Table.Td>{neighbor.local_as}</Table.Td>
                      <Table.Td>{neighbor.neighbor_as}</Table.Td>
                      <Table.Td>
                        <Badge color={bgpStateColors[neighbor.state] || 'gray'}>
                          {neighbor.state}
                        </Badge>
                      </Table.Td>
                      <Table.Td>{neighbor.prefixes_received}</Table.Td>
                      <Table.Td>{formatUptime(neighbor.uptime)}</Table.Td>
                    </Table.Tr>
                  ))
                )}
              </Table.Tbody>
            </Table>
          </Paper>
        </Tabs.Panel>

        <Tabs.Panel value="ospf" pt="md">
          <Paper shadow="sm" radius="md">
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Device</Table.Th>
                  <Table.Th>Neighbor IP</Table.Th>
                  <Table.Th>Router ID</Table.Th>
                  <Table.Th>Area</Table.Th>
                  <Table.Th>State</Table.Th>
                  <Table.Th>Uptime</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {ospfNeighbors.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={6} ta="center" py="xl">
                      <Text c="dimmed">No OSPF neighbors configured</Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  ospfNeighbors.map((neighbor) => (
                    <Table.Tr key={neighbor.id}>
                      <Table.Td>Device #{neighbor.device_id}</Table.Td>
                      <Table.Td fw={500}>{neighbor.neighbor_ip}</Table.Td>
                      <Table.Td>{neighbor.neighbor_id}</Table.Td>
                      <Table.Td>{neighbor.area_id || '0.0.0.0'}</Table.Td>
                      <Table.Td>
                        <Badge color={ospfStateColors[neighbor.state] || 'gray'}>
                          {neighbor.state}
                        </Badge>
                      </Table.Td>
                      <Table.Td>{formatUptime(neighbor.uptime)}</Table.Td>
                    </Table.Tr>
                  ))
                )}
              </Table.Tbody>
            </Table>
          </Paper>
        </Tabs.Panel>

        <Tabs.Panel value="eigrp" pt="md">
          <Paper shadow="sm" radius="md">
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Device</Table.Th>
                  <Table.Th>Neighbor IP</Table.Th>
                  <Table.Th>AS Number</Table.Th>
                  <Table.Th>Uptime</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {eigrpNeighbors.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={4} ta="center" py="xl">
                      <Text c="dimmed">No EIGRP neighbors configured</Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  eigrpNeighbors.map((neighbor) => (
                    <Table.Tr key={neighbor.id}>
                      <Table.Td>Device #{neighbor.device_id}</Table.Td>
                      <Table.Td fw={500}>{neighbor.neighbor_ip}</Table.Td>
                      <Table.Td>{neighbor.autonomous_system}</Table.Td>
                      <Table.Td>{formatUptime(neighbor.uptime)}</Table.Td>
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
