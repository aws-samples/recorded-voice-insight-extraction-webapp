import { Header, SpaceBetween } from "@cloudscape-design/components";
import RouterButton from "../../components/wrappers/router-button";
import RouterButtonDropdown from "../../components/wrappers/router-button-dropdown";

export default function DashboardHeader() {
  return (
    <Header
      variant="h1"
      actions={
        <SpaceBetween direction="horizontal" size="xs">
          <RouterButton href="/section1">View Items</RouterButton>
          <RouterButtonDropdown
            items={[
              {
                id: "add-data",
                text: "Add Item",
                href: "/section1/add",
              },
            ]}
          >
            Add data
          </RouterButtonDropdown>
        </SpaceBetween>
      }
    >
      Dashboard
    </Header>
  );
}
