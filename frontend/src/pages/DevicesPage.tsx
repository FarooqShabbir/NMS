import { useState, useEffect } from 'react'
import {
  Box,
  Title,
  Paper,
  Table,
  Group,
  Button,
  Modal,
  TextInput,
  Select,
  Text,
  Badge,
  ActionIcon,
  Tooltip,
  Loader,
} from '@mantine/core'
import { IconPlus, IconRefresh, IconTrash, IconEdit, IconServer } from '@tabler/icons-react'
import { api } from '../store/auth'
import { notifications } from '@mantine/notifications'
import dayjs from 'dayjs'

interface Device {
  id: number
  name: string
  ip_address: string
  device_type: string
  status: string
  location?: string
  created_at: string
}

const deviceTypes = [
  { value: 'router', label: 'Router' },
  { value: 'switch', label: 'Switch' },
  { value: 'firewall', label: 'Firewall' },
  { value: 'server', label: 'Server' },
  { value: 'access_point', label: 'Access Point' },
  { value: 'printer', label: 'Printer' },
  { value: 'other', label: 'Other' },
]

const statusColors: Record<string, string> = {
  up: 'green',
  down: 'red',
  warning: 'orange',
  unknown: 'gray',
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpened, setModalOpened] = useState(false)
  const [editingDevice, setEditingDevice] = useState<Device | null>(null)

  const [formData, setFormData] = useState({
    name: '',
    ip_address: '',
    device_type: 'router',
    location: '',
    snmp_community: 'public',
    snmp_version: 'v2c',
  })

  useEffect(() => {
    fetchDevices()
  }, [])

  const fetchDevices = async () => {
    try {
      const response = await api.get('/devices')
      setDevices(response.data)
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to load devices',
        color: 'red',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    try {
      if (editingDevice) {
        await api.put(`/devices/${editingDevice.id}`, formData)
        notifications.show({ title: 'Success', message: 'Device updated', color: 'green' })
      } else {
        await api.post('/devices', formData)
        notifications.show({ title: 'Success', message: 'Device added', color: 'green' })
      }
      setModalOpened(false)
      setEditingDevice(null)
      setFormData({ name: '', ip_address: '', device_type: 'router', location: '', snmp_community: 'public', snmp_version: 'v2c' })
      fetchDevices()
    } catch (error: any) {
      notifications.show({
        title: 'Error',
        message: error.response?.data?.detail || 'Failed to save device',
        color: 'red',
      })
    }
  }

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Delete device "${name}"?`)) return

    try {
      await api.delete(`/devices/${id}`)
      notifications.show({ title: 'Success', message: 'Device deleted', color: 'green' })
      fetchDevices()
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to delete device',
        color: 'red',
      })
    }
  }

  const handleEdit = (device: Device) => {
    setEditingDevice(device)
    setFormData({
      name: device.name,
      ip_address: device.ip_address,
      device_type: device.device_type,
      location: device.location || '',
      snmp_community: 'public',
      snmp_version: 'v2c',
    })
    setModalOpened(true)
  }

  const openAddModal = () => {
    setEditingDevice(null)
    setFormData({ name: '', ip_address: '', device_type: 'router', location: '', snmp_community: 'public', snmp_version: 'v2c' })
    setModalOpened(true)
  }

  return (
    <div>
      <Group justify="space-between" mb="lg">
        <Title order={2}>Devices</Title>
        <Group>
          <Button variant="outline" leftSection={<IconRefresh size={18} />} onClick={fetchDevices}>
            Refresh
          </Button>
          <Button leftSection={<IconPlus size={18} />} onClick={openAddModal}>
            Add Device
          </Button>
        </Group>
      </Group>

      <Paper shadow="sm" radius="md">
        {loading ? (
          <Box style={{ padding: 40, textAlign: 'center' }}>
            <Loader />
          </Box>
        ) : (
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Name</Table.Th>
                <Table.Th>IP Address</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Location</Table.Th>
                <Table.Th>Added</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {devices.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={7} ta="center" py="xl">
                    <Text c="dimmed">No devices configured. Click "Add Device" to get started.</Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                devices.map((device) => (
                  <Table.Tr key={device.id}>
                    <Table.Td>
                      <Group gap="sm">
                        <IconServer size={18} />
                        <Text fw={500}>{device.name}</Text>
                      </Group>
                    </Table.Td>
                    <Table.Td>{device.ip_address}</Table.Td>
                    <Table.Td>
                      <Badge variant="light" color="blue">
                        {device.device_type}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Badge color={statusColors[device.status] || 'gray'}>
                        {device.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{device.location || '-'}</Table.Td>
                    <Table.Td>{dayjs(device.created_at).format('MMM D, YYYY')}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Tooltip label="Edit">
                          <ActionIcon variant="light" color="blue" onClick={() => handleEdit(device)}>
                            <IconEdit size={16} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Delete">
                          <ActionIcon variant="light" color="red" onClick={() => handleDelete(device.id, device.name)}>
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

      <Modal opened={modalOpened} onClose={() => setModalOpened(false)} title={editingDevice ? 'Edit Device' : 'Add Device'}>
        <Box>
          <TextInput
            label="Name"
            placeholder="e.g., Core Router 1"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            mb="md"
            required
          />
          <TextInput
            label="IP Address"
            placeholder="192.168.1.1"
            value={formData.ip_address}
            onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
            mb="md"
            required
          />
          <Select
            label="Device Type"
            data={deviceTypes}
            value={formData.device_type}
            onChange={(value) => setFormData({ ...formData, device_type: value || 'router' })}
            mb="md"
          />
          <TextInput
            label="Location"
            placeholder="e.g., Data Center A"
            value={formData.location}
            onChange={(e) => setFormData({ ...formData, location: e.target.value })}
            mb="md"
          />
          <TextInput
            label="SNMP Community"
            value={formData.snmp_community}
            onChange={(e) => setFormData({ ...formData, snmp_community: e.target.value })}
            mb="md"
          />
          <Group justify="flex-end" mt="xl">
            <Button variant="outline" onClick={() => setModalOpened(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>
              {editingDevice ? 'Update' : 'Add'} Device
            </Button>
          </Group>
        </Box>
      </Modal>
    </div>
  )
}
