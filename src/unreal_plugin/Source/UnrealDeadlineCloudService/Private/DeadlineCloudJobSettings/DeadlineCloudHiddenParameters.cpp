#include "DeadlineCloudJobSettings/DeadlineCloudHiddenParameters.h"

bool FHiddenItemsManager::IsDefaultState() const
{
    if (!OnGetDefaultHidden.IsBound())
    {
        return Hidden.IsEmpty();
    }
    const TSet<FName> Defaults = OnGetDefaultHidden.Execute();
    return Hidden.Difference(Defaults).IsEmpty() && Defaults.Difference(Hidden).IsEmpty();
}

bool FHiddenItemsManager::IsDefaultForParameter(FName Name) const
{
    if (!OnGetDefaultHidden.IsBound())
        return !Hidden.Contains(Name);

    const TSet<FName> Defaults = OnGetDefaultHidden.Execute();
    const bool bHiddenByDefault = Defaults.Contains(Name);
    const bool bHiddenNow = Hidden.Contains(Name);
    return bHiddenNow == bHiddenByDefault;
}

void FHiddenItemsManager::PruneUnknown()
{
    if (!OnGetAllNames.IsBound()) return;
    const TSet<FName> All = OnGetAllNames.Execute();
    for (auto It = Hidden.CreateIterator(); It; ++It)
    {
        if (!All.Contains(*It))
            It.RemoveCurrent();
    }
    Changed();
}
