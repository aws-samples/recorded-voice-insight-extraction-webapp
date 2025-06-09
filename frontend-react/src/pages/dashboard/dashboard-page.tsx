import { APP_NAME } from "../../common/constants";
import {
  BreadcrumbGroup,
  ContentLayout,
  SpaceBetween,
} from "@cloudscape-design/components";
import { useOnFollow } from "../../common/hooks/use-on-follow";
import BaseAppLayout from "../../components/base-app-layout";
import DashboardHeader from "./dashboard-header";
import ItemsTable from "./items-table";
import StatisticsBlock from "./statistics-block";

export default function DashboardPage() {
  const onFollow = useOnFollow();

  return (
    <BaseAppLayout
      breadcrumbs={
        <BreadcrumbGroup
          onFollow={onFollow}
          items={[
            {
              text: APP_NAME,
              href: "/",
            },
          ]}
        />
      }
      content={
        <ContentLayout header={<DashboardHeader />}>
          <SpaceBetween size="l">
            <StatisticsBlock />
            <ItemsTable />
          </SpaceBetween>
        </ContentLayout>
      }
    />
  );
}
