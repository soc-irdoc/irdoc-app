import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'

/**
 * SSO configuration has moved to Integrations → Single Sign-On.
 * This component redirects there for any legacy route hits.
 */
export function SSOPage() {
  const navigate = useNavigate()
  useEffect(() => {
    navigate('/admin/integrations?section=identity', { replace: true })
  }, [navigate])
  return null
}
