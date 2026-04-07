import { useState } from 'react'
import { Box, Paper, TextInput, PasswordInput, Button, Text, Center } from '@mantine/core'
import { IconRouter, IconLock } from '@tabler/icons-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { notifications } from '@mantine/notifications'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await login(username, password)
      notifications.show({
        title: 'Login successful',
        message: `Welcome back, ${username}!`,
        color: 'green',
      })
      navigate('/')
    } catch (error: any) {
      let errorMsg = 'Invalid credentials'
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (typeof detail === 'string') {
          errorMsg = detail
        } else if (Array.isArray(detail) && detail.length > 0 && detail[0].msg) {
          errorMsg = detail[0].msg
        } else {
          errorMsg = JSON.stringify(detail)
        }
      }

      notifications.show({
        title: 'Login failed',
        message: errorMsg,
        color: 'red',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Center style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)' }}>
      <Paper
        shadow="xl"
        radius="lg"
        p="xl"
        style={{ width: 400 }}
      >
        <Center mb="xl">
          <Box
            style={{
              width: 64,
              height: 64,
              borderRadius: 16,
              background: 'linear-gradient(135deg, #228be6, #15aabf)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <IconRouter size={32} color="white" />
          </Box>
        </Center>

        <Text ta="center" fz="xl" fw={700} mb="sm">
          Network Monitoring System
        </Text>
        <Text ta="center" c="dimmed" mb="xl">
          Sign in to access your dashboard
        </Text>

        <form onSubmit={handleSubmit}>
          <TextInput
            label="Username"
            placeholder="admin"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            mb="md"
            size="lg"
          />
          <PasswordInput
            label="Password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            mb="xl"
            size="lg"
          />
          <Button
            type="submit"
            fullWidth
            size="lg"
            loading={loading}
            leftSection={<IconLock size={18} />}
          >
            Sign In
          </Button>
        </form>

        <Text ta="center" c="dimmed" size="xs" mt="xl">
          Default credentials: admin / admin123
        </Text>
      </Paper>
    </Center>
  )
}
