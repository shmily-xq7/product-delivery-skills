// Child page receives the actual API adapter from its parent route element.
import UserManagement from '../UserManagement'
import type { UserManagementProps } from '../UserManagement'
export default function TabContent(props: UserManagementProps) { return <UserManagement {...props} /> }
