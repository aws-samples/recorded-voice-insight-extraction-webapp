import { useEffect, useState } from "react";
import { signOut, fetchAuthSession } from "aws-amplify/auth";
import {
  ButtonDropdownProps,
  TopNavigation,
  Box,
} from "@cloudscape-design/components";
import { Mode } from "@cloudscape-design/global-styles";
import { StorageHelper } from "../common/helpers/storage-helper";
import { APP_NAME } from "../common/constants";
import { useOnFollow } from "../common/hooks/use-on-follow";

const StyledAppTitle = () => (
  <Box display="inline">
    <Box color="text-status-error" display="inline">RE</Box>
    <Box color="text-body-secondary" display="inline">corded </Box>
    <Box color="text-status-error" display="inline">V</Box>
    <Box color="text-body-secondary" display="inline">oice </Box>
    <Box color="text-status-error" display="inline">I</Box>
    <Box color="text-body-secondary" display="inline">nsight </Box>
    <Box color="text-status-error" display="inline">E</Box>
    <Box color="text-body-secondary" display="inline">xtraction </Box>
    <Box color="text-status-error" display="inline">W</Box>
    <Box color="text-body-secondary" display="inline">ebapp</Box>
  </Box>
);

export default function GlobalHeader() {
  const onFollow = useOnFollow();
  const [userName, setUserName] = useState<string | null>(null);
  const [theme, setTheme] = useState<Mode>(StorageHelper.getTheme());

  useEffect(() => {
    (async () => {
      const session = await fetchAuthSession();

      if (!session) {
        signOut();
        return;
      }

      setUserName(session.tokens?.idToken?.payload?.email?.toString() ?? "");
    })();
  }, []);

  const onChangeThemeClick = () => {
    if (theme === Mode.Dark) {
      setTheme(StorageHelper.applyTheme(Mode.Light));
    } else {
      setTheme(StorageHelper.applyTheme(Mode.Dark));
    }
  };

  const onUserProfileClick = ({
    detail,
  }: {
    detail: ButtonDropdownProps.ItemClickDetails;
  }) => {
    if (detail.id === "signout") {
      signOut();
    }
  };

  return (
    <div
      style={{ zIndex: 1002, top: 0, left: 0, right: 0, position: "fixed" }}
      id="awsui-top-navigation"
    >
      <TopNavigation
        identity={{
          href: "/",
          title: <StyledAppTitle />,
        }}
        utilities={[
          {
            type: "button",
            text: theme === Mode.Dark ? "Light Mode" : "Dark Mode",
            onClick: onChangeThemeClick,
          },
          {
            type: "menu-dropdown",
            description: userName ?? "",
            iconName: "user-profile",
            onItemClick: onUserProfileClick,
            items: [
              {
                id: "signout",
                text: "Sign out",
              },
            ],
            onItemFollow: onFollow,
          },
        ]}
      />
    </div>
  );
}
