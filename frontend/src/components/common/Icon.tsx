import type { IconBaseProps, IconType } from 'react-icons'

/** Renders an icon chosen at runtime (e.g. from a type → icon map). Decorative by default. */
export function Icon({ icon: Component, ...props }: IconBaseProps & { icon: IconType }) {
  return <Component aria-hidden="true" {...props} />
}
