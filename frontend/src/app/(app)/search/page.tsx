import { SearchWorkspace } from "@/features/search/components/SearchWorkspace";
import { SEARCH_PAGE_SECTIONS } from "@/app/(app)/search/sections";

export default function SearchPage() {
  return (
    <div data-section={SEARCH_PAGE_SECTIONS[0]}>
      <SearchWorkspace />
    </div>
  );
}
